from pathlib import Path
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

# Columnas que componen Movimientos
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



def cargar_datos() -> pd.DataFrame:
    """Carga datos desde archivos de SALDO BANCOS y calcula 'Movimientos'.
    Requiere columnas: Empresa, Fecha, Cuenta, Saldo Inicial, Saldo Libros y columnas de MOV_COLS si existen.
    Retorna DataFrame con columnas finales: Empresa, Fecha (Final), Fecha Inicial, Cuenta, Saldo Inicial, Movimientos, Saldo Libros."""
    archivos = [f for f in SALDO_BANCOS_DIR.glob('*.xlsx') if not f.name.startswith('~$')]
    if not archivos:
        return pd.DataFrame(columns=['Empresa','Fecha','Cuenta','Saldo Inicial','Movimientos','Saldo Libros'])
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
            # 1) Exacta
            for c in raw.columns:
                if c.strip().lower() == 'banco':
                    col_banco = c
                    break
            # 2) Fallback: columnas que contienen 'banco' pero NO 'cuenta'
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
            # Fecha Inicial (columna creada previamente en pipeline) puede o no estar
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
                # buscar case-insensitive
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
                col_fecha: 'Fecha',  # Será tratada como Fecha Final
                col_cuenta: 'Cuenta',
                col_saldo_inicial: 'Saldo Inicial',
                col_saldo_libros: 'Saldo Libros'
            }
            if 'col_fecha_inicial' in locals() and col_fecha_inicial:
                rename_map[col_fecha_inicial] = 'Fecha Inicial'
            if col_banco:
                rename_map[col_banco] = 'Banco'
            df = raw[keep_cols].rename(columns=rename_map)
            # Limpieza numérica
            # Limpieza numérica: SOLO cambiar coma decimal a punto, NO eliminar puntos (para no perder decimales)
            for col in ['Saldo Inicial','Saldo Libros'] + available_movs:
                if col in df.columns:
                    df[col] = (df[col].astype(str)
                                        .str.strip()
                                        .str.replace('\u00a0','', regex=False)  # espacios duros
                                        .str.replace(',', '.', regex=False))
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            # Asegurar tipo float (aunque sean enteros) para conservar .00 en formateo
            for col in ['Saldo Inicial','Saldo Libros'] + ['Movimientos']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            # Calcular Movimientos + Adiciones (positivos) y Salidas (negativos)
            if available_movs:
                movimientos_src = df[available_movs]
                df['Adiciones'] = movimientos_src.clip(lower=0).sum(axis=1, min_count=1)
                df['Salidas'] = movimientos_src.clip(upper=0).sum(axis=1, min_count=1)  # valores <= 0 (suma negativa)
                df['Movimientos'] = movimientos_src.sum(axis=1, min_count=1)
            else:
                df['Adiciones'] = 0.0
                df['Salidas'] = 0.0
                df['Movimientos'] = 0.0
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            if 'Fecha Inicial' in df.columns:
                df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], dayfirst=True, errors='coerce')
            df.dropna(subset=['Fecha'], inplace=True)
            # Orden preliminar (Variacion se calculará tras la agregación final):
            base_cols = ['Empresa','Fecha'] \
                        + (['Fecha Inicial'] if 'Fecha Inicial' in df.columns else []) \
                        + (['Banco'] if 'Banco' in df.columns else []) + [
                'Cuenta','Saldo Inicial','Adiciones','Salidas','Movimientos','Saldo Libros'
            ]
            frames.append(df[base_cols])
        except Exception as e:
            print(f"⚠️ Error leyendo {f.name}: {e}")
    if not frames:
        return pd.DataFrame(columns=['Empresa','Fecha','Fecha Inicial','Cuenta','Adiciones','Salidas','Saldo Inicial','Movimientos','Saldo Libros'])
    data = pd.concat(frames, ignore_index=True)
    # Agregar (sumar) por Empresa, Fecha Final, Fecha Inicial (si existe) y Cuenta
    group_cols = [c for c in ['Empresa','Fecha','Fecha Inicial','Banco','Cuenta'] if c in data.columns]
    agg_map = {'Adiciones':'sum','Salidas':'sum','Saldo Inicial':'sum','Movimientos':'sum','Saldo Libros':'sum'}
    data = data.groupby(group_cols, as_index=False).agg(agg_map)
    # Calcular Variacion (%). Evitar división por cero.
    import numpy as np
    data['Variacion'] = np.where((data['Saldo Inicial'] != 0) & (~data['Saldo Inicial'].isna()),
                                 (data['Movimientos'] / data['Saldo Inicial']) * 100,
                                 float('nan'))
    sort_cols = [c for c in ['Fecha','Empresa','Cuenta'] if c in data.columns]
    data.sort_values(sort_cols, inplace=True)
    return data


def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].unique()) if not df.empty else []
    fechas = sorted(df['Fecha'].dt.date.unique()) if not df.empty else []
    bancos = sorted(df['Banco'].unique()) if (not df.empty and 'Banco' in df.columns) else []
    # Fecha Inicial mostrada por defecto: si hay varias, la mínima
    fecha_inicial_default = None
    if not df.empty and 'Fecha Inicial' in df.columns and df['Fecha Inicial'].notna().any():
        fecha_inicial_default = df['Fecha Inicial'].min().date().strftime('%Y-%m-%d')

    # Datos iniciales para la tabla (aplican mismo filtrado CXP y totalización que en callback)
    if not df.empty:
        if 'Cuenta' in df.columns:
            df_init = df[~df['Cuenta'].str.contains('CXP', case=False, na=False)].copy()
        else:
            df_init = df.copy()
        if not df_init.empty:
            # Totales iniciales
            saldo_ini_sum = df_init['Saldo Inicial'].sum() if 'Saldo Inicial' in df_init.columns else 0.0
            mov_sum = df_init['Movimientos'].sum() if 'Movimientos' in df_init.columns else 0.0
            adiciones_sum = df_init['Adiciones'].sum() if 'Adiciones' in df_init.columns else 0.0
            salidas_sum = df_init['Salidas'].sum() if 'Salidas' in df_init.columns else 0.0
            saldo_libros_sum = df_init['Saldo Libros'].sum() if 'Saldo Libros' in df_init.columns else 0.0
            variacion_total = (mov_sum / saldo_ini_sum * 100.0) if saldo_ini_sum not in (0,0.0) else None
            data_records = (df_init.assign(Fecha=lambda d: d['Fecha'].dt.strftime('%Y-%m-%d')) \
                                   .drop([c for c in ['Empresa','Fecha','Fecha Inicial','Banco'] if c in df_init.columns], axis=1)
                                   .to_dict('records'))
            data_records.append({
                'Cuenta':'TOTAL',
                'Saldo Inicial': float(saldo_ini_sum),
                'Adiciones': float(adiciones_sum),
                'Salidas': float(salidas_sum),
                'Movimientos': float(mov_sum),
                'Variacion': variacion_total,
                'Saldo Libros': float(saldo_libros_sum)
            })
        else:
            data_records = []
    else:
        data_records = []
    return html.Div([
        html.H2('Cuadro de Movimientos y Saldos Bancarios'),
        html.Div([
            html.Div([
                html.Label('Empresas'),
                dcc.Dropdown(
                    id='cb-empresa-dropdown',
                    options=[{'label': e, 'value': e} for e in empresas],
                    value=empresas,
                    multi=True,
                    placeholder='Seleccione empresas'
                )
            ], style={'flex':1,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Banco'),
                dcc.Dropdown(
                    id='cb-banco-dropdown',
                    options=[{'label': b, 'value': b} for b in bancos],
                    value=bancos,
                    multi=True,
                    placeholder='Seleccione banco(s)'
                )
            ], style={'flex':1,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Fecha Final'),
                dcc.Dropdown(
                    id='cb-fecha-dropdown',
                    options=[{'label': f.strftime('%Y-%m-%d'), 'value': f.strftime('%Y-%m-%d')} for f in fechas],
                    value=(fechas[-1].strftime('%Y-%m-%d') if fechas else None),
                    multi=False,
                    clearable=False,
                    placeholder='Seleccione fecha final'
                )
            ], style={'flex':1,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Button('Actualizar datos', id='cb-refresh-btn', n_clicks=0, style={'marginTop':'22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'12px','maxWidth':'1100px','marginBottom':'10px'}),
        html.Div([
            html.Span('Fecha Inicial:', style={'fontWeight':'600','marginRight':'6px'}),
            html.Span(fecha_inicial_default or '—', id='cb-fecha-inicial-card')
        ], style={'marginBottom':'4px','background':'#f5f7fa','padding':'6px 12px','border':'1px solid #d9e1ec','borderRadius':'6px','display':'inline-block','fontSize':'13px','marginLeft':'210px'}),
        dcc.Loading(dash_table.DataTable(
            id='cuadro-bancos-table',
            columns=[
                {'name':'Cuenta','id':'Cuenta'},
                ({'name':'Saldo Inicial','id':'Saldo Inicial','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Saldo Inicial','id':'Saldo Inicial'}),
                ({'name':'Adiciones','id':'Adiciones','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Adiciones','id':'Adiciones'}),
                ({'name':'Salidas','id':'Salidas','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Salidas','id':'Salidas'}),
                ({'name':'Movimientos','id':'Movimientos','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Movimientos','id':'Movimientos'}),
                ({'name':'Variacion %','id':'Variacion','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Variacion %','id':'Variacion'}),
                ({'name':'Saldo Libros','id':'Saldo Libros','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Saldo Libros','id':'Saldo Libros'}),
            ],
            data=data_records,
            sort_action='native',
            filter_action='none',
            page_action='native',
            page_size=25,
            style_table={'overflowX':'auto','border':'0px','padding':'4px'},
            style_header={'backgroundColor':'#f5f7fa','fontWeight':'600','border':'1px solid #d9e1ec','borderRadius':'4px'},
            style_cell={'padding':'6px 10px','fontFamily':'Arial','fontSize':'13px','border':'1px solid #edf0f5'},
            style_data={'backgroundColor':'white'},
            style_data_conditional=[
                {'if': {'filter_query': '{Movimientos} < 0','column_id':'Movimientos'}, 'color':'#b30000','fontWeight':'600'},
                {'if': {'filter_query': '{Saldo Libros} < 0','column_id':'Saldo Libros'}, 'color':'#b30000','fontWeight':'600'},
                {'if': {'filter_query': '{Salidas} < 0','column_id':'Salidas'}, 'color':'#b30000','fontWeight':'600'},
                {'if': {'filter_query': '{Variacion} < 0','column_id':'Variacion'}, 'color':'#b30000','fontWeight':'600'},
                {'if': {'filter_query': '{Cuenta} = "TOTAL"'}, 'fontWeight':'700','backgroundColor':'#eef3f9'}
            ],
            css=[{'selector':'.dash-table-container','rule':'padding:4px;'}]
        )),
        dcc.Store(id='cb-data-store')
    ], style={'fontFamily':'Arial','padding':'18px'})


def register(app):
    @app.callback(
        Output('cb-data-store','data'),
        Input('cb-refresh-btn','n_clicks'),
        prevent_initial_call=False
    )
    def refrescar(_):
        df = cargar_datos()
        return df.to_json(date_format='iso', orient='split')

    @app.callback(
        Output('cuadro-bancos-table','data'),
        Output('cb-fecha-inicial-card','children'),
        Input('cb-data-store','data'),
        Input('cb-empresa-dropdown','value'),
        Input('cb-banco-dropdown','value'),
        Input('cb-fecha-dropdown','value')
    )
    def actualizar(data_json, empresas_sel, bancos_sel, fecha_sel):
        if not data_json:
            return [], '—'
        df = pd.read_json(data_json, orient='split')
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        if 'Fecha Inicial' in df.columns:
            df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        if bancos_sel and 'Banco' in df.columns:
            df = df[df['Banco'].isin(bancos_sel)]
        if fecha_sel:
            try:
                fecha_dt = pd.to_datetime([fecha_sel], errors='coerce')[0].normalize()
                if pd.notna(fecha_dt):
                    df = df[df['Fecha'].dt.normalize() == fecha_dt]
            except Exception:
                pass
        if df.empty:
            return [], '—'
        df = df.sort_values(['Fecha','Empresa','Cuenta'])
        fecha_inicial_card = '—'
        if 'Fecha Inicial' in df.columns and df['Fecha Inicial'].notna().any():
            fecha_inicial_card = df['Fecha Inicial'].min().strftime('%Y-%m-%d')
        # Recalcular variacion sobre el subconjunto filtrado (por si se filtra Empresa / Fecha)
        if 'Saldo Inicial' in df.columns and 'Movimientos' in df.columns:
            import numpy as np
            df['Variacion'] = np.where((df['Saldo Inicial'] != 0) & (~df['Saldo Inicial'].isna()),
                                       (df['Movimientos'] / df['Saldo Inicial']) * 100,
                                       float('nan'))
        # Filtrar CXP en Cuenta
        if 'Cuenta' in df.columns:
            df = df[~df['Cuenta'].str.contains('CXP', case=False, na=False)]
        # Totales
        total_row = {}
        if not df.empty:
            saldo_ini_sum = df['Saldo Inicial'].sum() if 'Saldo Inicial' in df.columns else 0.0
            mov_sum = df['Movimientos'].sum() if 'Movimientos' in df.columns else 0.0
            adiciones_sum = df['Adiciones'].sum() if 'Adiciones' in df.columns else 0.0
            salidas_sum = df['Salidas'].sum() if 'Salidas' in df.columns else 0.0
            saldo_libros_sum = df['Saldo Libros'].sum() if 'Saldo Libros' in df.columns else 0.0
            variacion_total = (mov_sum / saldo_ini_sum * 100.0) if saldo_ini_sum not in (0,0.0) else None
            total_row = {
                'Cuenta':'TOTAL',
                'Saldo Inicial': float(saldo_ini_sum),
                'Adiciones': float(adiciones_sum),
                'Salidas': float(salidas_sum),
                'Movimientos': float(mov_sum),
                'Variacion': variacion_total,
                'Saldo Libros': float(saldo_libros_sum)
            }
        table_data = (df.assign(Fecha=lambda d: d['Fecha'].dt.strftime('%Y-%m-%d'))
                         .drop([c for c in ['Empresa','Fecha','Fecha Inicial','Banco'] if c in df.columns], axis=1)
                         .to_dict('records'))
        if total_row:
            table_data.append(total_row)
        return table_data, fecha_inicial_card

__all__ = ["layout","register"]
