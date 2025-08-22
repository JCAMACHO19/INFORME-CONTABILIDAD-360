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
        html.H2(
            'Distribución saldos bancarios',
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
                    value=None,  # Sin selección inicial para ver todo
                    multi=True,
                    placeholder='Empresas'
                )
            ], style={'flex':2,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Bancos'),
                dcc.Dropdown(
                    id='banco-dropdown',
                    options=[{'label': b, 'value': b} for b in bancos],
                    value=None,  # Sin selección inicial para ver todo
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
        PCT_LABEL_MIN = 8.0  # umbral ligeramente mayor para evitar ruido visual
        grp['LabelPct'] = grp['% Empresa'].apply(lambda v: f"{v:.1f}%" if pd.notna(v) and v >= PCT_LABEL_MIN else '')
        # Porcentaje para tooltip: mismo cálculo y redondeo que la etiqueta interna (1 decimal), pero sin ocultarlo
        grp['PctTooltip'] = grp['% Empresa'].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else '')
        # Formatos para tooltip minimalista
        def fmt_moneda_es(v: float) -> str:
            try:
                s = f"{v:,.0f}"
                return "$" + s.replace(",", ".")
            except Exception:
                return "$0"
        grp['SaldoFmt'] = grp['Saldo Libros'].apply(fmt_moneda_es)
        # Paleta moderna y elegante solicitada
        palette = [
            "#B2B2B4",  # Gris medio
            "#1965B4",  # Azul intenso
            "#31356D",  # Azul marino oscuro
            "#5B90C4",  # Azul acero claro
            "#41BCE7",  # Cian medio
            "#2E609A",  # Azul acero medio
            "#2D8CB9",  # Azul cielo profundo
            "#41B7D6",  # Cian medio
            "#6BE6E8",  # Cian claro
        ]
        # Formatear fecha seleccionada para el título
        meses_es = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
        titulo_fecha = None
        try:
            if fecha_sel:
                fdt = pd.to_datetime([fecha_sel])[0]
                titulo_fecha = f"{fdt.day} de {meses_es[fdt.month-1]} de {fdt.year}"
        except Exception:
            titulo_fecha = fecha_sel
        fig = px.bar(
            grp,
            x='Empresa',
            y='Saldo Libros',
            color='Banco',
            barmode='stack',
            text='LabelPct',
            title=None,
            color_discrete_sequence=palette,
            # Pasar custom_data por fila para mantener alineación punto a punto en cada traza
            custom_data=['Empresa', 'SaldoFmt', 'PctTooltip']
        )
        # Hover personalizado
        fig.update_traces(
            # En hovermode='x unified' el encabezado muestra la Empresa una sola vez (x),
            # y cada línea debe mostrar: Banco – $Saldo (Pct)
            hovertemplate=(
                "%{fullData.name} – %{customdata[1]} (%{customdata[2]})<extra></extra>"
            ),
            textposition='inside',
            textfont=dict(color='#ffffff', size=11),
            insidetextanchor='middle'
        )
    # Añadir totales sobre cada barra (formato $ entero) por empresa
        tot_por_emp = grp.groupby('Empresa')['Saldo Libros'].sum()
        for emp, total in tot_por_emp.items():
            fig.add_annotation(
        x=emp,
        y=total,
        text=fmt_moneda_es(total),
        showarrow=False,
        yshift=12,
        yanchor='bottom',
                font=dict(size=11, color='#000000'),
        bgcolor='#ffffff',
        bordercolor='#d0d7de',
        borderwidth=1,
        borderpad=2,
            )
        # Título como anotación centrada debajo del eje X (sin fondo)
        titulo_graf = f"Total Saldos a {titulo_fecha}" if titulo_fecha else 'Total Saldos'
        fig.update_layout(
            xaxis_title='Empresa',
            yaxis_title='Saldo Libros',
            legend_title='Banco',
            hovermode='x unified',
            bargap=0.18,
            plot_bgcolor='#ffffff',
            paper_bgcolor='#fafbfc',
            font=dict(
                family="'Coolvetica','Montserrat','Helvetica Neue','Arial',sans-serif",
                size=12,
                color='#222'
            ),
            legend=dict(
                borderwidth=0,
                itemclick='toggleothers',
                orientation='h',
                yanchor='bottom', y=1.02,
                x=0
            ),
            margin=dict(l=60, r=40, t=70, b=120),
            annotations=[
                dict(
                    text=titulo_graf,
                    xref='paper', yref='paper', x=0.5, y=-0.18,
                    showarrow=False,
                    font=dict(
                        size=14,
                        color='#0f1b33',
                        family="'Coolvetica','Montserrat','Helvetica Neue','Arial',sans-serif"
                    ),
                    align='center'
                )
            ]
        )
        fig.update_xaxes(showgrid=False, linecolor='#d0d7de')
        fig.update_yaxes(showgrid=True, gridcolor='#eef2f5', zerolinecolor='#d0d7de')
        return fig

__all__ = ["layout", "register"]
