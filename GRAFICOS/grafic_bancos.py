from pathlib import Path
import pandas as pd
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go

# ------------------ Configuración de rutas ------------------
BASE_DIR = Path(__file__).resolve().parent
SALDO_BANCOS_DIR = BASE_DIR.parent / 'INFORME BANCOS' / 'SALDO BANCOS'

if not SALDO_BANCOS_DIR.exists():
    raise FileNotFoundError(f'No se encontró la carpeta de datos: {SALDO_BANCOS_DIR}')

# ------------------ Carga de datos ------------------

def cargar_datos() -> pd.DataFrame:
    """Carga y normaliza datos incluyendo Saldo Inicial y Saldo Libros.
    Retorna columnas: Empresa, Fecha (datetime), Saldo Inicial, Saldo Libros"""
    archivos = [f for f in SALDO_BANCOS_DIR.glob('*.xlsx') if not f.name.startswith('~$')]
    if not archivos:
        return pd.DataFrame(columns=['Empresa', 'Fecha', 'Saldo Inicial', 'Saldo Libros'])
    frames = []
    for f in archivos:
        try:
            df = pd.read_excel(f, dtype=str)
            columnas_map = {c.lower().strip(): c for c in df.columns}
            col_empresa = columnas_map.get('empresa')
            col_fecha = columnas_map.get('fecha')
            posibles_inicial = [k for k in columnas_map.keys() if k.replace(' ', '') in ('saldoinicial','saldo_inicial')]
            col_saldo_inicial = columnas_map.get('saldo inicial') or columnas_map.get('saldoinicial')
            if not col_saldo_inicial and posibles_inicial:
                col_saldo_inicial = columnas_map[posibles_inicial[0]]
            col_saldo_libros = None
            for c in df.columns:
                if c.strip().lower() == 'saldo libros':
                    col_saldo_libros = c
                    break
            if not (col_empresa and col_fecha and col_saldo_inicial and col_saldo_libros):
                continue
            sub = df[[col_empresa, col_fecha, col_saldo_inicial, col_saldo_libros]].rename(columns={
                col_empresa: 'Empresa',
                col_fecha: 'Fecha',
                col_saldo_inicial: 'Saldo Inicial',
                col_saldo_libros: 'Saldo Libros'
            })
            for cnum in ['Saldo Inicial', 'Saldo Libros']:
                sub[cnum] = (sub[cnum].astype(str)
                                  .str.strip()
                                  .str.replace('\u00a0','', regex=False)
                                  .str.replace(',', '.', regex=False))
                sub[cnum] = pd.to_numeric(sub[cnum], errors='coerce')
            # Asegurar floats
            for cnum in ['Saldo Inicial','Saldo Libros']:
                sub[cnum] = sub[cnum].astype(float)
            sub['Fecha'] = pd.to_datetime(sub['Fecha'], dayfirst=True, errors='coerce')
            sub.dropna(subset=['Fecha', 'Saldo Libros', 'Saldo Inicial'], inplace=True)
            frames.append(sub)
        except Exception as e:
            print(f'⚠️ Error leyendo {f.name}: {e}')
    if not frames:
        return pd.DataFrame(columns=['Empresa', 'Fecha', 'Saldo Inicial', 'Saldo Libros'])
    data = pd.concat(frames, ignore_index=True)
    data = (data.groupby(['Empresa', 'Fecha'], as_index=False)
                 .agg({'Saldo Inicial': 'sum', 'Saldo Libros': 'sum'}))
    data.sort_values(['Fecha', 'Empresa'], inplace=True)
    return data

# ------------------ Layout ------------------

def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].dropna().unique()) if not df.empty else []
    fechas = sorted(df['Fecha'].dt.date.unique()) if not df.empty else []
    return html.Div([
        html.H2('Saldo Inicial vs Saldo Libros'),
        html.Div([
            html.Div([
                html.Label('Empresas'),
                dcc.Dropdown(
                    id='empresa-dropdown',
                    options=[{'label': e, 'value': e} for e in empresas],
                    value=empresas,
                    multi=True,
                    placeholder='Seleccione empresas'
                )
            ], style={'flex':1, 'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Fechas'),
                dcc.Dropdown(
                    id='fecha-dropdown',
                    options=[{'label': f.strftime('%Y-%m-%d'), 'value': f.strftime('%Y-%m-%d')} for f in fechas],
                    value=[f.strftime('%Y-%m-%d') for f in fechas],
                    multi=True,
                    placeholder='Seleccione fechas'
                )
            ], style={'flex':1, 'minWidth':'250px'}),
            html.Div([
                html.Button('Actualizar datos', id='refresh-btn', n_clicks=0, style={'marginTop': '22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'12px','maxWidth':'900px'}),
        dcc.Loading(dcc.Graph(id='grafico-barras-apiladas')),
        dcc.Store(id='data-store'),
    ], style={'fontFamily': 'Arial', 'padding': '18px'})

# ------------------ Registro de callbacks ------------------

def register(app):
    @app.callback(
        Output('data-store', 'data'),
        Input('refresh-btn', 'n_clicks'),
        prevent_initial_call=False
    )
    def refrescar_datos(_):
        df = cargar_datos()
        return df.to_json(date_format='iso', orient='split')

    @app.callback(
        Output('grafico-barras-apiladas', 'figure'),
        Input('data-store', 'data'),
        Input('empresa-dropdown', 'value'),
        Input('fecha-dropdown', 'value')
    )
    def actualizar_barras(data_json, empresas_sel, fechas_sel):
        if not data_json:
            return px.bar(title='Sin datos disponibles')
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
            return px.bar(title='Sin datos para los filtros')
        df['Variacion %'] = ((df['Saldo Libros'] - df['Saldo Inicial']) / df['Saldo Inicial'].replace({0: pd.NA})) * 100
        df['Variacion %'] = df['Variacion %'].fillna(0)
        long_df = df.melt(id_vars=['Empresa', 'Fecha', 'Variacion %'], value_vars=['Saldo Inicial', 'Saldo Libros'],
                          var_name='Tipo', value_name='Valor')
        long_df['Etiqueta'] = long_df['Empresa'] + ' | ' + long_df['Fecha'].dt.strftime('%Y-%m-%d')
        long_df.sort_values(['Fecha','Empresa','Tipo'], inplace=True)
        fig = px.bar(long_df, x='Etiqueta', y='Valor', color='Tipo', barmode='stack',
                     color_discrete_map={'Saldo Inicial':'#1f77b4','Saldo Libros':'#ff7f0e'},
                     title='Saldo Inicial vs Saldo Libros (Barras Apiladas)')
        agreg = long_df.pivot_table(index='Etiqueta', columns='Tipo', values='Valor', aggfunc='sum').fillna(0)
        variaciones = (df[['Empresa','Fecha','Variacion %']]
                       .drop_duplicates()
                       .assign(Etiqueta=lambda d: d['Empresa'] + ' | ' + d['Fecha'].dt.strftime('%Y-%m-%d'))
                       .set_index('Etiqueta'))
        for etiqueta, row in agreg.iterrows():
            total = row.get('Saldo Inicial',0) + row.get('Saldo Libros',0)
            var_pct = variaciones.loc[etiqueta, 'Variacion %'] if etiqueta in variaciones.index else 0
            texto = f"{var_pct:.1f}%"
            fig.add_annotation(x=etiqueta, y=total, text=texto,
                               showarrow=False, yshift=4, font=dict(size=11,color='#222'))
        fig.update_layout(xaxis_title='Empresa | Fecha', yaxis_title='Valor', legend_title='Tipo',
                          hovermode='x unified', bargap=0.25)
        fig.update_traces(hovertemplate='%{x}<br>%{fullData.name}: %{y:,.2f}<extra></extra>')
        return fig

__all__ = ["layout", "register"]
