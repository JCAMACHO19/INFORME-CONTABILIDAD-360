from pathlib import Path
from io import StringIO
import pandas as pd
from dash import html, dcc, Input, Output
from dash import dash_table

# Formato numérico (intenta usar API avanzada; si falla, fallback a None)
try:
    from dash.dash_table.Format import Format, Scheme, Group  # type: ignore
    NUM_FORMAT = Format(precision=2, scheme=Scheme.fixed, group=Group.yes, nully='-')
except Exception:
    NUM_FORMAT = None

BASE_DIR = Path(__file__).resolve().parent
SALDO_BANCOS_DIR = BASE_DIR.parent / 'INFORME BANCOS' / 'SALDO BANCOS'

# Columnas que componen Movimientos (igual a cuadro_banc.py)
MOV_COLS = [
    'ABR - Notas contables',
    'Ajustes y Reclasificaciones',
    'CE CHEQUES',
    'CE TRANSF',
    'Comprobante de Egreso',
    'Cuenta Por Pagar',
    'Comprobante de Ingreso',
    'Documento de Cartera Reversado',
    'Gastos Bancarios',
    'GASTOS BANCARIOS AUTOMATICOS',
    'Legalizacion de anticipos',
    'Prestamos',
    'Traslado de Fondos',
]

# Formateo de fechas en español (texto largo)
MESES_ES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
def fecha_es(d) -> str:
    try:
        return f"{d.day} de {MESES_ES[d.month-1]} de {d.year}"
    except Exception:
        try:
            return d.strftime('%Y-%m-%d')
        except Exception:
            return str(d)


def cargar_datos() -> pd.DataFrame:
    """Carga datos desde archivos de SALDO BANCOS y calcula métricas base.
    Requiere columnas: Empresa, Fecha, Cuenta, Saldo Inicial, Saldo Libros y columnas de MOV_COLS si existen.
    Retorna DataFrame agregado por ['Empresa','Fecha','Fecha Inicial','Banco','Cuenta'] (las que existan) con columnas:
      ['Adiciones','Salidas','Saldo Inicial','Movimientos','Saldo Libros','Variacion']
    """
    archivos = [f for f in SALDO_BANCOS_DIR.glob('*.xlsx') if not f.name.startswith('~$')]
    if not archivos:
        return pd.DataFrame(columns=['Empresa','Fecha','Fecha Inicial','Banco','Cuenta','Adiciones','Salidas','Saldo Inicial','Movimientos','Saldo Libros','Variacion'])
    frames = []
    for f in archivos:
        try:
            raw = pd.read_excel(f, dtype=str)
            cols_map = {c.lower().strip(): c for c in raw.columns}
            col_empresa = cols_map.get('empresa')
            col_fecha = cols_map.get('fecha')
            # Cuenta puede venir como 'Cuenta' o 'Cuenta bancaria'
            col_cuenta = None
            for c in raw.columns:
                if c.strip().lower() in ('cuenta','cuenta bancaria','nombre cuenta','cuenta banco'):
                    col_cuenta = c
                    break
            # Banco: priorizar coincidencia EXACTA 'Banco'; evitar tomar columnas de cuenta que contengan 'banc'
            col_banco = None
            for c in raw.columns:
                if c.strip().lower() == 'banco':
                    col_banco = c
                    break
            if not col_banco:
                for c in raw.columns:
                    lc = c.strip().lower()
                    if 'banco' in lc and 'cuenta' not in lc:
                        col_banco = c
                        break
            # Saldo Inicial y Saldo Libros
            col_saldo_inicial = None
            for c in raw.columns:
                if c.strip().lower().replace(' ','') in ('saldoinicial','saldo_inicial'):
                    col_saldo_inicial = c
                    break
            col_saldo_libros = None
            for c in raw.columns:
                if c.strip().lower().replace(' ','') in ('saldolibros','saldo_libros'):
                    col_saldo_libros = c
                    break
            if not (col_empresa and col_fecha and col_cuenta and col_saldo_inicial and col_saldo_libros):
                continue
            # Fecha Inicial puede o no estar
            col_fecha_inicial = None
            for c in raw.columns:
                if c.strip().lower().replace('í','i') == 'fecha inicial':
                    col_fecha_inicial = c
                    break

            needed = [col_empresa, col_fecha, col_cuenta, col_saldo_inicial, col_saldo_libros] \
                      + ([col_fecha_inicial] if col_fecha_inicial else []) \
                      + ([col_banco] if col_banco else [])
            available_movs = []
            for mc in MOV_COLS:
                found = None
                for c in raw.columns:
                    if c.strip().lower() == mc.strip().lower():
                        found = c
                        break
                if found:
                    available_movs.append(found)
            keep_cols = needed + available_movs
            rename_map = {
                col_empresa: 'Empresa',
                col_fecha: 'Fecha',
                col_cuenta: 'Cuenta',
                col_saldo_inicial: 'Saldo Inicial',
                col_saldo_libros: 'Saldo Libros'
            }
            if 'col_fecha_inicial' in locals() and col_fecha_inicial:
                rename_map[col_fecha_inicial] = 'Fecha Inicial'
            if col_banco:
                rename_map[col_banco] = 'Banco'
            df = raw[keep_cols].rename(columns=rename_map)
            # Limpieza numérica: solo coma a punto
            for col in ['Saldo Inicial','Saldo Libros'] + available_movs:
                if col in df.columns:
                    df[col] = (df[col].astype(str)
                                        .str.strip()
                                        .str.replace('\u00a0','', regex=False)
                                        .str.replace(',', '.', regex=False))
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            # Asegurar tipo float
            for col in ['Saldo Inicial','Saldo Libros','Movimientos','Adiciones','Salidas']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            # Calcular Adiciones/Salidas/Movimientos
            if available_movs:
                movimientos_src = df[available_movs]
                df['Adiciones'] = movimientos_src.clip(lower=0).sum(axis=1, min_count=1)
                df['Salidas'] = movimientos_src.clip(upper=0).sum(axis=1, min_count=1)
                df['Movimientos'] = movimientos_src.sum(axis=1, min_count=1)
            else:
                df['Adiciones'] = 0.0
                df['Salidas'] = 0.0
                df['Movimientos'] = 0.0

            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            if 'Fecha Inicial' in df.columns:
                df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], dayfirst=True, errors='coerce')
            df.dropna(subset=['Fecha'], inplace=True)

            base_cols = ['Empresa','Fecha'] \
                        + (['Fecha Inicial'] if 'Fecha Inicial' in df.columns else []) \
                        + (['Banco'] if 'Banco' in df.columns else []) + [
                'Cuenta','Saldo Inicial','Adiciones','Salidas','Movimientos','Saldo Libros'
            ]
            frames.append(df[base_cols])
        except Exception as e:
            print(f"⚠️ Error leyendo {f.name}: {e}")

    if not frames:
        return pd.DataFrame(columns=['Empresa','Fecha','Fecha Inicial','Banco','Cuenta','Adiciones','Salidas','Saldo Inicial','Movimientos','Saldo Libros','Variacion'])

    data = pd.concat(frames, ignore_index=True)
    # Agregado base
    group_cols = [c for c in ['Empresa','Fecha','Fecha Inicial','Banco','Cuenta'] if c in data.columns]
    agg_map = {'Adiciones':'sum','Salidas':'sum','Saldo Inicial':'sum','Movimientos':'sum','Saldo Libros':'sum'}
    data = data.groupby(group_cols, as_index=False).agg(agg_map)

    # Variación (%): Movimientos / Saldo Inicial * 100
    import numpy as np
    data['Variacion'] = np.where((data['Saldo Inicial'] != 0) & (~data['Saldo Inicial'].isna()),
                                 (data['Movimientos'] / data['Saldo Inicial']) * 100,
                                 float('nan'))

    sort_cols = [c for c in ['Fecha','Empresa','Banco','Cuenta'] if c in data.columns]
    data.sort_values(sort_cols, inplace=True)
    return data


def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].unique()) if not df.empty else []
    fechas = sorted(df['Fecha'].dt.date.unique()) if not df.empty else []
    bancos = sorted(df['Banco'].unique()) if (not df.empty and 'Banco' in df.columns) else []

    # Fecha Inicial por defecto (mínima disponible)
    fecha_inicial_default = None
    if not df.empty and 'Fecha Inicial' in df.columns and df['Fecha Inicial'].notna().any():
        fecha_inicial_default = fecha_es(df['Fecha Inicial'].min().date())

    # Datos iniciales (vacío hasta primer refresh) – construiremos columnas básicas
    initial_columns = [{'name':'Empresa','id':'Empresa'}]
    if bancos:
        for b in bancos:
            initial_columns.append({'name': b, 'id': b} if NUM_FORMAT is None else {'name': b, 'id': b, 'type': 'numeric', 'format': NUM_FORMAT})
    initial_columns.append({'name':'TOTAL','id':'TOTAL'} if NUM_FORMAT is None else {'name':'TOTAL','id':'TOTAL','type':'numeric','format':NUM_FORMAT})

    return html.Div([
        html.H2(
            'Bancos por Empresa',
            style={
                'marginBottom': '8px',
                'fontFamily': "'Coolvetica','Montserrat','Helvetica Neue','Arial',sans-serif",
                'fontWeight': 600,
                'letterSpacing': '0.3px',
                'fontSize': 'clamp(18px, 2.4vw, 28px)',
                'color': '#111',
                'background': 'rgba(49, 53, 109, 0.12)',
                'padding': '8px 14px',
                'borderRadius': '10px',
                'textAlign': 'left',
                'boxShadow': '0 1px 6px rgba(0,0,0,0.04)'
            }
        ),
        html.Div([
            html.Div([
                html.Label('Empresas'),
                dcc.Dropdown(
                    id='be-empresa-dropdown',
                    options=[{'label': e, 'value': e} for e in empresas],
                    value=None,
                    multi=True,
                    placeholder='Empresas'
                )
            ], style={'flex':1,'minWidth':'240px','marginRight':'12px'}),
            html.Div([
                html.Label('Banco (columnas)'),
                dcc.Dropdown(
                    id='be-banco-dropdown',
                    options=[{'label': b, 'value': b} for b in bancos],
                    value=None,
                    multi=True,
                    placeholder='Bancos'
                )
            ], style={'flex':1,'minWidth':'240px','marginRight':'12px'}),
            html.Div([
                html.Label('Fecha Final'),
                dcc.Dropdown(
                    id='be-fecha-dropdown',
                    options=[{'label': fecha_es(f), 'value': f.strftime('%Y-%m-%d')} for f in fechas],
                    value=(fechas[-1].strftime('%Y-%m-%d') if fechas else None),
                    multi=False,
                    clearable=False,
                    placeholder='Seleccione fecha final'
                )
            ], style={'flex':1,'minWidth':'240px','marginRight':'12px'}),
            html.Div([
                html.Label('Métrica'),
                dcc.Dropdown(
                    id='be-metrica-dropdown',
                    options=[
                        {'label':'Saldo Inicial','value':'Saldo Inicial'},
                        {'label':'Entradas','value':'Adiciones'},
                        {'label':'Salidas','value':'Salidas'},
                        {'label':'Movimientos','value':'Movimientos'},
                        {'label':'Variacion %','value':'Variacion'},
                        {'label':'Saldo Libros','value':'Saldo Libros'},
                    ],
                    value='Saldo Libros',
                    multi=False,
                    clearable=False
                )
            ], style={'flex':1,'minWidth':'200px','marginRight':'12px'}),
            html.Div([
                html.Button('Actualizar datos', id='be-refresh-btn', n_clicks=0, style={'marginTop':'22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'12px','maxWidth':'1200px','marginBottom':'10px'}),
        html.Div([
            html.Span('Fecha Inicial:', style={'fontWeight':'600','marginRight':'6px'}),
            html.Span(fecha_inicial_default or '—', id='be-fecha-inicial-card')
        ], style={'marginBottom':'4px','background':'#f5f7fa','padding':'6px 12px','border':'1px solid #d9e1ec','borderRadius':'6px','display':'inline-block','fontSize':'13px'}),
        dcc.Loading(dash_table.DataTable(
            id='be-table',
            columns=initial_columns,
            data=[],
            sort_action='native',
            filter_action='none',
            page_action='native',
            page_size=25,
            style_table={'overflowX':'auto','border':'0px','padding':'4px'},
            style_header={'backgroundColor':'#f5f7fa','fontWeight':'600','border':'1px solid #d9e1ec','borderRadius':'4px','textAlign':'left'},
            style_cell={'padding':'6px 10px','fontFamily':'Arial','fontSize':'13px','border':'1px solid #edf0f5','textAlign':'left'},
            style_data={'backgroundColor':'white'},
            style_data_conditional=[
                # Negativos en TOTAL en rojo
                {'if': {'filter_query': '{TOTAL} < 0','column_id':'TOTAL'}, 'color':'#b30000'},
                # Toda la columna TOTAL en negrilla
                {'if': {'column_id': 'TOTAL'}, 'fontWeight':'700'},
                # Fila TOTAL completa en negrilla
                {'if': {'filter_query': '{Empresa} = "TOTAL"'}, 'fontWeight':'700'}
            ],
            css=[{'selector':'.dash-table-container','rule':'padding:4px;'}]
        )),
        dcc.Store(id='be-data-store')
    ], style={'fontFamily':'Arial','padding':'18px','backgroundColor':'#fafbfc','textAlign':'left'})


def register(app):
    @app.callback(
        Output('be-data-store','data'),
        Input('be-refresh-btn','n_clicks'),
        prevent_initial_call=False
    )
    def refrescar(_):
        df = cargar_datos()
        return df.to_json(date_format='iso', orient='split')

    @app.callback(
        Output('be-table','data'),
        Output('be-table','columns'),
        Output('be-fecha-inicial-card','children'),
        Input('be-data-store','data'),
        Input('be-empresa-dropdown','value'),
        Input('be-banco-dropdown','value'),
        Input('be-fecha-dropdown','value'),
        Input('be-metrica-dropdown','value')
    )
    def actualizar(data_json, empresas_sel, bancos_sel, fecha_sel, metrica):
        if not data_json:
            # columnas mínimas
            base_cols = [{'name':'Empresa','id':'Empresa'}]
            base_cols.append({'name':'TOTAL','id':'TOTAL'} if NUM_FORMAT is None else {'name':'TOTAL','id':'TOTAL','type':'numeric','format':NUM_FORMAT})
            return [], base_cols, '—'

        df = pd.read_json(StringIO(data_json), orient='split')
        # Tipos
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        if 'Fecha Inicial' in df.columns:
            df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
        df = df.dropna(subset=['Fecha'])

        # Filtros
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        if fecha_sel:
            try:
                fecha_dt = pd.to_datetime([fecha_sel], errors='coerce')[0].normalize()
                if pd.notna(fecha_dt):
                    df = df[df['Fecha'].dt.normalize() == fecha_dt]
            except Exception:
                pass
        if 'Cuenta' in df.columns:
            df = df[~df['Cuenta'].str.contains('CXP', case=False, na=False)]
        if bancos_sel and 'Banco' in df.columns:
            df = df[df['Banco'].isin(bancos_sel)]

        if df.empty:
            base_cols = [{'name':'Empresa','id':'Empresa'}]
            base_cols.append({'name':'TOTAL','id':'TOTAL'} if NUM_FORMAT is None else {'name':'TOTAL','id':'TOTAL','type':'numeric','format':NUM_FORMAT})
            return [], base_cols, '—'

        # Fecha Inicial card
        fecha_inicial_card = '—'
        if 'Fecha Inicial' in df.columns and df['Fecha Inicial'].notna().any():
            try:
                fecha_inicial_card = fecha_es(df['Fecha Inicial'].min().date())
            except Exception:
                fecha_inicial_card = df['Fecha Inicial'].min().strftime('%Y-%m-%d')

        # Construcción pivot segun métrica
        bancos_presentes = sorted(df['Banco'].dropna().unique()) if 'Banco' in df.columns else []
        if bancos_sel:
            bancos_presentes = [b for b in bancos_presentes if b in bancos_sel]

        # Para variación requerimos ratio de sumas por (Empresa,Banco)
        if metrica == 'Variacion':
            grp = df.groupby(['Empresa','Banco'], as_index=False).agg({'Movimientos':'sum','Saldo Inicial':'sum'})
            import numpy as np
            grp['Valor'] = np.where((grp['Saldo Inicial'] != 0) & (~grp['Saldo Inicial'].isna()),
                                    (grp['Movimientos'] / grp['Saldo Inicial']) * 100,
                                    float('nan'))
            pivot = grp.pivot(index='Empresa', columns='Banco', values='Valor')
            # No rellenar NaN para preservar '-' en formato; solo bancos seleccionados/ordenados
            pivot = pivot.reindex(columns=bancos_presentes)
            # Columna TOTAL: ratio ponderado por empresa
            tot_emp = df.groupby('Empresa', as_index=True).agg({'Movimientos':'sum','Saldo Inicial':'sum'})
            tot_emp['TOTAL'] = np.where((tot_emp['Saldo Inicial'] != 0) & (~tot_emp['Saldo Inicial'].isna()),
                                        (tot_emp['Movimientos'] / tot_emp['Saldo Inicial']) * 100,
                                        float('nan'))
            pivot['TOTAL'] = pivot.index.map(tot_emp['TOTAL']).astype(float)
            # Fila TOTAL: ratio ponderado global por banco + TOTAL global
            totals_by_bank = df.groupby('Banco', as_index=True).agg({'Movimientos':'sum','Saldo Inicial':'sum'})
            totals_row = {}
            for b in bancos_presentes:
                if b in totals_by_bank.index:
                    mov = totals_by_bank.loc[b, 'Movimientos']
                    si = totals_by_bank.loc[b, 'Saldo Inicial']
                    totals_row[b] = (mov / si * 100) if (pd.notna(si) and si != 0) else float('nan')
                else:
                    totals_row[b] = float('nan')
            mov_all = df['Movimientos'].sum()
            si_all = df['Saldo Inicial'].sum()
            totals_row['TOTAL'] = (mov_all / si_all * 100) if (pd.notna(si_all) and si_all != 0) else float('nan')
        else:
            # Otras métricas: sumar
            if metrica not in df.columns:
                # fallback
                metrica = 'Saldo Libros' if 'Saldo Libros' in df.columns else 'Movimientos'
            pivot = pd.pivot_table(df, index='Empresa', columns='Banco', values=metrica, aggfunc='sum', fill_value=0.0)
            pivot = pivot.reindex(columns=bancos_presentes, fill_value=0.0)
            pivot['TOTAL'] = pivot.sum(axis=1, numeric_only=True)
            totals_row = {b: float(df.loc[df['Banco'] == b, metrica].sum()) for b in bancos_presentes}
            totals_row['TOTAL'] = float(df[metrica].sum())

        # Orden filas por Empresa
        pivot = pivot.sort_index()

        # Preparar columnas para DataTable
        columns = [{'name':'Empresa','id':'Empresa'}]
        for b in bancos_presentes:
            if NUM_FORMAT:
                columns.append({'name': b, 'id': b, 'type':'numeric', 'format': NUM_FORMAT})
            else:
                columns.append({'name': b, 'id': b})
        columns.append({'name':'TOTAL','id':'TOTAL'} if NUM_FORMAT is None else {'name':'TOTAL','id':'TOTAL','type':'numeric','format':NUM_FORMAT})

        # Convertir a records y añadir fila TOTAL
        table_df = pivot.reset_index()
        data_records = table_df.to_dict('records')
        # Añadir fila TOTAL al final
        total_row_record = {'Empresa': 'TOTAL'}
        total_row_record.update({k: (None if pd.isna(v) else float(v)) for k, v in totals_row.items()})
        data_records.append(total_row_record)

        return data_records, columns, fecha_inicial_card

__all__ = ["layout","register"]
