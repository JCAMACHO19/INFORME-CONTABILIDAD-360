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
    """Carga y normaliza datos incluyendo Saldo Libros y Banco.
    Retorna columnas: Empresa, Fecha (datetime), Banco, Saldo Libros, Saldo Inicial (opcional)."""
    archivos = [f for f in SALDO_BANCOS_DIR.glob('*.xlsx') if not f.name.startswith('~$')]
    if not archivos:
        return pd.DataFrame(columns=['Empresa', 'Fecha', 'Banco', 'Saldo Libros', 'Saldo Inicial'])
    frames = []
    for f in archivos:
        try:
            df = pd.read_excel(f, dtype=str)
            col_empresa = None
            col_fecha = None
            col_saldo_libros = None
            col_saldo_inicial = None
            col_banco = None
            col_cuenta = None
            for c in df.columns:
                key = c.strip().lower().replace('\u00a0','')
                if key == 'empresa':
                    col_empresa = c
                elif key == 'fecha':
                    col_fecha = c
                elif key in ('saldo libros','saldolibros','saldo_libros'):
                    col_saldo_libros = c
                elif key in ('saldo inicial','saldoinicial','saldo_inicial'):
                    col_saldo_inicial = c
                elif key in ('banco','nombrebanco','nombre banco','cuenta bancaria','cuentabancaria') and col_banco is None:
                    col_banco = c
                elif key in ('cuenta','cuenta bancaria','cuentabanco','cuentabancaria','nombre cuenta') and col_cuenta is None:
                    col_cuenta = c
            if not (col_empresa and col_fecha and col_saldo_libros):
                continue
            if not col_banco:
                # Si no hay banco, crear una columna default
                df['__BancoTmp__'] = 'Sin Banco'
                col_banco = '__BancoTmp__'
            cols_select = [col_empresa, col_fecha, col_banco, col_saldo_libros] + ([col_saldo_inicial] if col_saldo_inicial else []) + ([col_cuenta] if col_cuenta else [])
            sub = df[cols_select].rename(columns={
                col_empresa: 'Empresa',
                col_fecha: 'Fecha',
                col_banco: 'Banco',
                col_saldo_libros: 'Saldo Libros',
                **({col_saldo_inicial: 'Saldo Inicial'} if col_saldo_inicial else {}),
                **({col_cuenta: 'Cuenta'} if col_cuenta else {})
            })
            # Limpieza numérica
            for cnum in [c for c in ['Saldo Libros','Saldo Inicial'] if c in sub.columns]:
                sub[cnum] = (sub[cnum].astype(str)
                                    .str.strip()
                                    .str.replace('\u00a0','', regex=False)
                                    .str.replace(',', '.', regex=False))
                sub[cnum] = pd.to_numeric(sub[cnum], errors='coerce')
                sub[cnum] = sub[cnum].astype(float)
            sub['Fecha'] = pd.to_datetime(sub['Fecha'], dayfirst=True, errors='coerce')
            sub.dropna(subset=['Fecha', 'Saldo Libros'], inplace=True)
            # Filtrar cuentas que contengan 'CXP'
            if 'Cuenta' in sub.columns:
                sub = sub[~sub['Cuenta'].str.contains('CXP', case=False, na=False)]
            if sub.empty:
                continue
            frames.append(sub[['Empresa','Fecha','Banco'] + ([ 'Saldo Inicial'] if 'Saldo Inicial' in sub.columns else []) + ['Saldo Libros']])
        except Exception as e:
            print(f'⚠️ Error leyendo {f.name}: {e}')
    if not frames:
        return pd.DataFrame(columns=['Empresa', 'Fecha', 'Banco', 'Saldo Libros', 'Saldo Inicial'])
    data = pd.concat(frames, ignore_index=True)
    # Agregar sumas por Empresa, Fecha, Banco
    agg_cols = {'Saldo Libros':'sum'}
    if 'Saldo Inicial' in data.columns:
        agg_cols['Saldo Inicial'] = 'sum'
    data = (data.groupby(['Empresa','Fecha','Banco'], as_index=False)
                 .agg(agg_cols))
    data.sort_values(['Fecha','Empresa','Banco'], inplace=True)
    return data

# ------------------ Layout ------------------

def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].dropna().unique()) if not df.empty else []
    fechas = sorted(df['Fecha'].dt.date.unique()) if not df.empty else []
    bancos = sorted(df['Banco'].dropna().unique()) if (not df.empty and 'Banco' in df.columns) else []
    # Formateo amigable en español: 'DD de mes de YYYY'
    meses_es = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    def fecha_es(d):
        return f"{d.day} de {meses_es[d.month-1]} de {d.year}"
    fecha_default = fechas[-1].strftime('%Y-%m-%d') if fechas else None
    return html.Div([
        html.H2('Distribución Saldo Libros por Empresa y Banco', style={'marginBottom':'8px'}),
        html.Div([
            html.Div([
                html.Label('Fecha (única)'),
                dcc.Dropdown(
                    id='fecha-dropdown',
                    options=[{'label': fecha_es(f), 'value': f.strftime('%Y-%m-%d')} for f in fechas],
                    value=fecha_default,
                    clearable=False,
                    placeholder='Seleccione fecha'
                )
            ], style={'flex':1,'minWidth':'170px','marginRight':'12px'}),
            html.Div([
                html.Label('Empresas'),
                dcc.Dropdown(
                    id='empresa-dropdown',
                    options=[{'label': e, 'value': e} for e in empresas],
                    value=empresas,
                    multi=True,
                    placeholder='Empresas'
                )
            ], style={'flex':2,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Bancos'),
                dcc.Dropdown(
                    id='banco-dropdown',
                    options=[{'label': b, 'value': b} for b in bancos],
                    value=bancos,
                    multi=True,
                    placeholder='Bancos'
                )
            ], style={'flex':2,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Button('Actualizar datos', id='refresh-btn', n_clicks=0, style={'marginTop':'22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'10px','maxWidth':'1200px','alignItems':'flex-start','marginBottom':'10px'}),
        dcc.Loading(dcc.Graph(id='grafico-bancos-stacked', style={'height':'620px'}), type='dot'),
        dcc.Store(id='data-store'),
    ], style={'fontFamily': 'Arial', 'padding': '18px','backgroundColor':'#fafbfc'})

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
        Output('grafico-bancos-stacked', 'figure'),
        Input('data-store', 'data'),
        Input('fecha-dropdown', 'value'),
        Input('empresa-dropdown', 'value'),
        Input('banco-dropdown', 'value')
    )
    def actualizar_barras(data_json, fecha_sel, empresas_sel, bancos_sel):
        if not data_json:
            return px.bar(title='Sin datos disponibles')
        df = pd.read_json(data_json, orient='split')
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        # Filtro fecha única
        if fecha_sel:
            try:
                fecha_dt = pd.to_datetime([fecha_sel], errors='coerce')[0]
                df = df[df['Fecha'].dt.normalize() == fecha_dt.normalize()]
            except Exception:
                pass
        # Filtro empresas
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        # Filtro bancos
        if bancos_sel and 'Banco' in df.columns:
            df = df[df['Banco'].isin(bancos_sel)]
        if df.empty:
            return px.bar(title='Sin datos tras filtros')
        # Agrupar para gráfico
        grp = (df.groupby(['Empresa','Banco'], as_index=False)
                 .agg({'Saldo Libros':'sum'}))
        # Ordenar empresas por total descendente
        totales = grp.groupby('Empresa')['Saldo Libros'].sum().sort_values(ascending=False)
        orden_empresas = list(totales.index)
        grp['Empresa'] = pd.Categorical(grp['Empresa'], categories=orden_empresas, ordered=True)
        # Calcular porcentaje dentro de empresa
        grp['% Empresa'] = grp['Saldo Libros'] / grp.groupby('Empresa')['Saldo Libros'].transform('sum') * 100
        # Etiquetas internas: mostrar solo si el segmento tiene suficiente porcentaje
        PCT_LABEL_MIN = 7.0  # umbral mínimo en % para mostrar texto dentro
        grp['LabelPct'] = grp['% Empresa'].apply(lambda v: f"{v:.1f}%" if pd.notna(v) and v >= PCT_LABEL_MIN else '')
        palette = px.colors.qualitative.Safe + px.colors.qualitative.Set2 + px.colors.qualitative.Pastel
        # Formatear fecha seleccionada para el título
        meses_es = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
        titulo_fecha = None
        try:
            if fecha_sel:
                fdt = pd.to_datetime([fecha_sel])[0]
                titulo_fecha = f"{fdt.day} de {meses_es[fdt.month-1]} de {fdt.year}"
        except Exception:
            titulo_fecha = fecha_sel
        fig = px.bar(grp, x='Empresa', y='Saldo Libros', color='Banco', barmode='stack', text='LabelPct',
                     title=f"Saldo Libros por Empresa y Banco ({titulo_fecha})" if titulo_fecha else 'Saldo Libros por Empresa y Banco',
                     color_discrete_sequence=palette)
        # Hover personalizado
        fig.update_traces(hovertemplate=('Empresa: %{x}<br>Banco: %{fullData.name}<br>'
                                         'Saldo Libros: %{y:,.2f}<br>Participación: %{customdata[0]:.1f}%<extra></extra>'),
                          customdata=grp[['% Empresa']].to_numpy(),
                          textposition='inside',
                          textfont=dict(color='#ffffff', size=11))
        # Añadir totales sobre cada barra
        tot_por_emp = grp.groupby('Empresa')['Saldo Libros'].sum()
        for emp, total in tot_por_emp.items():
            fig.add_annotation(x=emp, y=total, text=f"{total:,.2f}", showarrow=False,
                               yshift=5, font=dict(size=11,color='#222'))
        fig.update_layout(
            xaxis_title='Empresa', yaxis_title='Saldo Libros', legend_title='Banco',
            hovermode='x unified', bargap=0.25,
            plot_bgcolor='#ffffff', paper_bgcolor='#fafbfc',
            font=dict(family='Arial', size=12, color='#222'),
            legend=dict(borderwidth=0, itemclick='toggleothers', orientation='h', yanchor='bottom', y=1.02, x=0)
        )
        fig.update_xaxes(showgrid=False, linecolor='#d0d7de')
        fig.update_yaxes(showgrid=True, gridcolor='#eef2f5', zerolinecolor='#d0d7de')
        return fig

__all__ = ["layout", "register"]
