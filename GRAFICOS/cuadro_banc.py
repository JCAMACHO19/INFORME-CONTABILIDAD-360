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
    'Cheques x Ent'
]



def cargar_datos() -> pd.DataFrame:
    """Carga datos desde archivos de SALDO BANCOS y calcula 'Movimientos'.
    Requiere columnas: Empresa, Fecha, Cuenta, Saldo Inicial, Saldo Libros y columnas de MOV_COLS si existen.
    Retorna DataFrame con columnas finales: Empresa, Fecha, Cuenta, Saldo Inicial, Movimientos, Saldo Libros."""
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
            needed = [col_empresa, col_fecha, col_cuenta, col_saldo_inicial, col_saldo_libros]
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
            df = raw[keep_cols].rename(columns={
                col_empresa: 'Empresa',
                col_fecha: 'Fecha',
                col_cuenta: 'Cuenta',
                col_saldo_inicial: 'Saldo Inicial',
                col_saldo_libros: 'Saldo Libros'
            })
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
            # Calcular Movimientos
            if available_movs:
                df['Movimientos'] = df[available_movs].sum(axis=1, min_count=1)
            else:
                df['Movimientos'] = 0
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df.dropna(subset=['Fecha'], inplace=True)
            frames.append(df[['Empresa','Fecha','Cuenta','Saldo Inicial','Movimientos','Saldo Libros']])
        except Exception as e:
            print(f"⚠️ Error leyendo {f.name}: {e}")
    if not frames:
        return pd.DataFrame(columns=['Empresa','Fecha','Cuenta','Saldo Inicial','Movimientos','Saldo Libros'])
    data = pd.concat(frames, ignore_index=True)
    # Agregar (sumar) por Empresa, Fecha y Cuenta
    data = (data.groupby(['Empresa','Fecha','Cuenta'], as_index=False)
                 .agg({'Saldo Inicial':'sum','Movimientos':'sum','Saldo Libros':'sum'}))
    data.sort_values(['Fecha','Empresa','Cuenta'], inplace=True)
    return data


def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].unique()) if not df.empty else []
    fechas = sorted(df['Fecha'].dt.date.unique()) if not df.empty else []
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
                html.Label('Fechas'),
                dcc.Dropdown(
                    id='cb-fecha-dropdown',
                    options=[{'label': f.strftime('%Y-%m-%d'), 'value': f.strftime('%Y-%m-%d')} for f in fechas],
                    value=[f.strftime('%Y-%m-%d') for f in fechas],
                    multi=True,
                    placeholder='Seleccione fechas'
                )
            ], style={'flex':1,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Button('Actualizar datos', id='cb-refresh-btn', n_clicks=0, style={'marginTop':'22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'12px','maxWidth':'1100px','marginBottom':'10px'}),
        dcc.Loading(dash_table.DataTable(
            id='cuadro-bancos-table',
            columns=[
                {'name':'Empresa','id':'Empresa'},
                {'name':'Fecha','id':'Fecha'},
                {'name':'Cuenta','id':'Cuenta'},
                ({'name':'Saldo Inicial','id':'Saldo Inicial','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Saldo Inicial','id':'Saldo Inicial'}),
                ({'name':'Movimientos','id':'Movimientos','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Movimientos','id':'Movimientos'}),
                ({'name':'Saldo Libros','id':'Saldo Libros','type':'numeric','format':NUM_FORMAT} if NUM_FORMAT else {'name':'Saldo Libros','id':'Saldo Libros'}),
            ],
            data=df.assign(Fecha=lambda d: d['Fecha'].dt.strftime('%Y-%m-%d')).to_dict('records') if not df.empty else [],
            sort_action='native',
            filter_action='none',
            page_action='native',
            page_size=25,
            style_table={'overflowX':'auto','border':'0px','padding':'4px'},
            style_header={'backgroundColor':'#f5f7fa','fontWeight':'600','border':'1px solid #d9e1ec','borderRadius':'4px'},
            style_cell={'padding':'6px 10px','fontFamily':'Arial','fontSize':'13px','border':'1px solid #edf0f5'},
            style_data={'backgroundColor':'white'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Movimientos} < 0','column_id':'Movimientos'},
                    'color':'#b30000','fontWeight':'600'
                },
                {
                    'if': {'filter_query': '{Saldo Libros} < 0','column_id':'Saldo Libros'},
                    'color':'#b30000','fontWeight':'600'
                }
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
        Input('cb-data-store','data'),
        Input('cb-empresa-dropdown','value'),
        Input('cb-fecha-dropdown','value')
    )
    def actualizar(data_json, empresas_sel, fechas_sel):
        if not data_json:
            return []
        df = pd.read_json(data_json, orient='split')
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        if fechas_sel:
            fechas_dt = pd.to_datetime(fechas_sel, errors='coerce')
            fechas_dt = fechas_dt[~pd.isna(fechas_dt)].normalize()
            if len(fechas_dt) > 0:
                df = df[df['Fecha'].dt.normalize().isin(fechas_dt)]
        if df.empty:
            return []
        df = df.sort_values(['Fecha','Empresa','Cuenta'])
        return df.assign(Fecha=lambda d: d['Fecha'].dt.strftime('%Y-%m-%d')).to_dict('records')

__all__ = ["layout","register"]
