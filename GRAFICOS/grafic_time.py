from pathlib import Path
import io
import pandas as pd
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import cuadro_banc

BASE_DIR = Path(__file__).resolve().parent


def cargar_datos() -> pd.DataFrame:
    df = cuadro_banc.cargar_datos()
    if df.empty:
        return pd.DataFrame(columns=['Empresa','Fecha','Fecha Inicial','Banco','Saldo Inicial','Saldo Libros','Movimientos'])
    # Filtro CXP
    if 'Cuenta' in df.columns:
        df = df[~df['Cuenta'].str.contains('CXP', case=False, na=False)]
    # Tipos
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if 'Fecha Inicial' in df.columns:
        df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
    for c in ['Saldo Inicial','Saldo Libros','Movimientos']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    if 'Banco' not in df.columns:
        df['Banco'] = 'Sin Banco'
    # Devolver sin agrupar; el callback agregará por serie
    df = df.dropna(subset=['Fecha'])
    df.sort_values(['Fecha','Empresa'], inplace=True)
    return df


def layout():
    df = cargar_datos()
    empresas = sorted(df['Empresa'].dropna().unique()) if not df.empty else []
    bancos = sorted(df['Banco'].dropna().unique()) if (not df.empty and 'Banco' in df.columns) else []
    return html.Div([
        html.H2('Evolución de Saldo Libros y Movimientos'),
        html.Div([
            html.Div([
                html.Label('Empresas'),
                dcc.Dropdown(
                    id='gt-empresa-dropdown',
                    options=[{'label': e, 'value': e} for e in empresas],
                    value=empresas,
                    multi=True
                )
            ], style={'flex':2,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Label('Bancos'),
                dcc.Dropdown(
                    id='gt-banco-dropdown',
                    options=[{'label': b, 'value': b} for b in bancos],
                    value=bancos,
                    multi=True
                )
            ], style={'flex':2,'minWidth':'250px','marginRight':'12px'}),
            html.Div([
                html.Button('Actualizar datos', id='gt-refresh-btn', n_clicks=0, style={'marginTop':'22px'})
            ])
        ], style={'display':'flex','flexWrap':'wrap','gap':'10px','maxWidth':'1200px','alignItems':'flex-start','marginBottom':'10px'}),
        dcc.Loading(dcc.Graph(id='grafico-time', style={'height':'620px'}), type='dot'),
        dcc.Store(id='gt-data')
    ], style={'fontFamily':'Arial','padding':'18px'})


def register(app):
    @app.callback(
        Output('gt-data','data'),
        Input('gt-refresh-btn','n_clicks'),
        prevent_initial_call=False
    )
    def refrescar(_):
        df = cargar_datos()
        return df.to_json(date_format='iso', orient='split')

    @app.callback(
        Output('grafico-time','figure'),
        Input('gt-data','data'),
        Input('gt-empresa-dropdown','value'),
        Input('gt-banco-dropdown','value')
    )
    def actualizar(data_json, empresas_sel, bancos_sel):
        if not data_json:
            return go.Figure()
        df = pd.read_json(io.StringIO(data_json), orient='split')
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        if 'Fecha Inicial' in df.columns:
            df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
        # Asegurar numéricos
        for c in ['Saldo Libros','Saldo Inicial','Movimientos']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        if bancos_sel:
            df = df[df['Banco'].isin(bancos_sel)]
        if df.empty:
            return go.Figure()
        # Construir periodos YYYY-MM para agrupar categorías
        df['PeriodoLib'] = df['Fecha'].dt.to_period('M').astype(str)
        if 'Fecha Inicial' in df.columns:
            df['PeriodoIni'] = df['Fecha Inicial'].dt.to_period('M').astype(str)
        palette = px.colors.qualitative.Safe + px.colors.qualitative.Set2 + px.colors.qualitative.Pastel
        empresas = sorted(df['Empresa'].unique())
        color_map = {emp: palette[i % len(palette)] for i, emp in enumerate(empresas)}
        # Selección por mes: Inicial = primer día encontrado; Libros = último día encontrado, por Empresa/Banco/mes
        # Luego, agregar por Empresa para las barras apiladas
        grp_ini = pd.DataFrame()
        if 'PeriodoIni' in df.columns and 'Saldo Inicial' in df.columns:
            dfi = df.dropna(subset=['PeriodoIni', 'Fecha Inicial']).copy()
            if not dfi.empty:
                # Obtener la fecha inicial mínima por Empresa/Banco/Periodo
                min_dates = dfi.groupby(['Empresa', 'Banco', 'PeriodoIni'])['Fecha Inicial'].transform('min')
                dfi_firstday = dfi[dfi['Fecha Inicial'] == min_dates]
                # Agregar por periodo y empresa (suma de todas las filas de ese día)
                grp_ini = dfi_firstday.groupby(['PeriodoIni', 'Empresa'], as_index=False)['Saldo Inicial'].sum()
        grp_lib = pd.DataFrame()
        if 'Saldo Libros' in df.columns:
            dflb = df.dropna(subset=['PeriodoLib', 'Fecha']).copy()
            if not dflb.empty:
                # Obtener la fecha máxima por Empresa/Banco/Periodo
                max_dates = dflb.groupby(['Empresa', 'Banco', 'PeriodoLib'])['Fecha'].transform('max')
                dfl_lastday = dflb[dflb['Fecha'] == max_dates]
                # Agregar por periodo y empresa (suma de todas las filas de ese día)
                grp_lib = dfl_lastday.groupby(['PeriodoLib', 'Empresa'], as_index=False)['Saldo Libros'].sum()
        # Categorías unificadas y orden cronológico basadas en subconjuntos filtrados
        cats = set()
        if not grp_lib.empty:
            cats.update(grp_lib['PeriodoLib'].dropna().unique())
        if not grp_ini.empty:
            cats.update(grp_ini['PeriodoIni'].dropna().unique())
        cats = sorted(cats)
        fig = go.Figure()
        # Serie 1: Saldo Inicial por periodo (primero, más opaco)
        if not grp_ini.empty:
            for emp in empresas:
                dfe = grp_ini[grp_ini['Empresa'] == emp]
                if dfe.empty:
                    continue
                fig.add_bar(
                    name=f"{emp} - Inicial",
                    x=dfe['PeriodoIni'],
                    y=dfe['Saldo Inicial'],
                    marker_color=color_map[emp],
                    opacity=0.55,
                    offsetgroup='inicial',
                    legendgroup=f"{emp}-inicial",
                    hovertemplate='Periodo: %{x}<br>Empresa: %{fullData.name}<br>Saldo Inicial: %{y:,.2f}<extra></extra>'
                )
        # Serie 2: Saldo Libros por periodo (después)
        if not grp_lib.empty:
            for emp in empresas:
                dfe = grp_lib[grp_lib['Empresa'] == emp]
                if dfe.empty:
                    continue
                fig.add_bar(
                    name=f"{emp} - Libros",
                    x=dfe['PeriodoLib'],
                    y=dfe['Saldo Libros'],
                    marker_color=color_map[emp],
                    opacity=0.55,
                    offsetgroup='libros',
                    legendgroup=f"{emp}-libros",
                    hovertemplate='Periodo: %{x}<br>Empresa: %{fullData.name}<br>Saldo Libros: %{y:,.2f}<extra></extra>'
                )
        # Totales por pila (suma de todas las empresas) para posicionamiento y rótulos
        tot_ini = {}
        if not grp_ini.empty:
            tot_ini = grp_ini.groupby('PeriodoIni')['Saldo Inicial'].sum().to_dict()
        tot_lib = {}
        if not grp_lib.empty:
            tot_lib = grp_lib.groupby('PeriodoLib')['Saldo Libros'].sum().to_dict()

        # Línea: Movimientos total por periodo y etiquetas como Variación % (sum(Mov)/sum(Saldo Inicial)*100)
        period_agg = df.groupby('PeriodoLib', as_index=False).agg({'Movimientos': 'sum', 'Saldo Inicial': 'sum'})
        # Asegurar que los periodos de la línea estén presentes en el orden del eje X
        if not period_agg.empty:
            cats = sorted(set(cats).union(set(period_agg['PeriodoLib'].dropna().unique())))
        # Calcular banda superior del eje Y principal para ubicar visualmente la línea
        y1_max_data = 0.0
        if len(tot_ini):
            y1_max_data = max(y1_max_data, max(tot_ini.values()))
        if len(tot_lib):
            y1_max_data = max(y1_max_data, max(tot_lib.values()))
        if y1_max_data <= 0:
            y1_max_data = float(df['Saldo Libros'].sum()) if 'Saldo Libros' in df.columns else 1.0
        band_min = y1_max_data * 0.86
        band_max = y1_max_data * 0.98
        mv_min = float(period_agg['Movimientos'].min()) if not period_agg.empty else 0.0
        mv_max = float(period_agg['Movimientos'].max()) if not period_agg.empty else 1.0
        if mv_min == mv_max:
            mv_max = mv_min + 1.0
        def scale_to_band(v: float) -> float:
            return band_min + ((v - mv_min) / (mv_max - mv_min)) * (band_max - band_min)

        # Etiquetas porcentaje con coma decimal y posiciones intercaladas
        labels_pct = []
        positions = []
        line_y = []
        for i, (_, row) in enumerate(period_agg.iterrows()):
            si = row.get('Saldo Inicial', 0.0)
            mv = row.get('Movimientos', 0.0)
            line_y.append(scale_to_band(float(mv)))
            if pd.notna(si) and si not in (0, 0.0):
                val = (mv / si) * 100.0
                labels_pct.append((f"{val:.2f}%").replace('.', ','))
            else:
                labels_pct.append('')
            positions.append('top center' if i % 2 == 0 else 'bottom center')

        fig.add_trace(go.Scatter(
            x=period_agg['PeriodoLib'], y=line_y, name='Movimientos',
            mode='lines+markers+text', text=labels_pct, textposition=positions,
            textfont=dict(size=10, color='#2ca02c'),
            line=dict(color='#2ca02c', width=2)
        ))

        # Variación total (%): Movimientos / Saldo Inicial del subconjunto filtrado
        saldo_ini_sum = float(df['Saldo Inicial'].sum()) if 'Saldo Inicial' in df.columns else 0.0
        mov_sum = float(df['Movimientos'].sum()) if 'Movimientos' in df.columns else 0.0
        variacion_total = (mov_sum / saldo_ini_sum * 100.0) if saldo_ini_sum not in (0, 0.0) else None

        # Layout: dos pilas apiladas lado a lado por periodo (via offsetgroup)
        titulo = 'Saldo Libros vs Saldo Inicial por periodo (apilados por Empresa), y Movimientos mensual'
        if variacion_total is not None:
            titulo += " | Variación total: " + (f"{variacion_total:.2f}%".replace('.', ','))
        fig.update_layout(barmode='stack',
                          title=titulo,
                          xaxis_title='Periodo (YYYY-MM)', yaxis_title='Valor', legend_title='Serie',
                          plot_bgcolor='#ffffff', paper_bgcolor='#fafbfc',
                          font=dict(family='Arial', size=12, color='#222'),
                          hovermode='x unified',
                          margin=dict(l=60, r=40, t=80, b=150))
        # Formateo de ticks a 'Mes YYYY' en español
        meses_es = {
            '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr', '05': 'May', '06': 'Jun',
            '07': 'Jul', '08': 'Ago', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
        }
        def fmt_periodo(p):
            s = str(p)
            parts = s.split('-')
            if len(parts) >= 2:
                yy = parts[0]
                mm = parts[1].zfill(2)
                return f"{meses_es.get(mm, mm)} {yy}"
            return s
        tickvals = cats
        ticktext = [fmt_periodo(p) for p in cats]
        fig.update_xaxes(showgrid=False, linecolor='#d0d7de', type='category',
                         categoryorder='array', categoryarray=cats,
                         tickmode='array', tickvals=tickvals, ticktext=ticktext,
                         ticklabelposition='outside bottom', ticks='outside', ticklen=16,
                         automargin=True)
        # Calcular rango del eje Y principal con holgura para no cortar las etiquetas superiores
        max_bar = 0.0
        if len(tot_ini):
            max_bar = max(max_bar, max(tot_ini.values()))
        if len(tot_lib):
            max_bar = max(max_bar, max(tot_lib.values()))
        y1_range = None
        if max_bar and max_bar != float('inf'):
            y1_range = [0, max_bar * 1.15]
        fig.update_yaxes(showgrid=True, gridcolor='#eef2f5', zerolinecolor='#d0d7de', rangemode='tozero', range=y1_range)
        # Eje secundario removido; se usa mapeo a banda superior del eje principal para la línea

        # Anotaciones: etiquetas base "Saldo Inicial" / "Saldo Final" y totales arriba en millones
        annotations = []
        for per in cats:
            # Total arriba de cada pila
            if per in tot_ini:
                annotations.append(dict(
                    x=per, y=tot_ini[per], xref='x', yref='y',
                    text=f"{tot_ini[per]/1_000_000:.1f} M", showarrow=False,
                    yshift=6, font=dict(size=11, color='#1f77b4')
                ))
            if per in tot_lib:
                annotations.append(dict(
                    x=per, y=tot_lib[per], xref='x', yref='y',
                    text=f"{tot_lib[per]/1_000_000:.1f} M", showarrow=False,
                    yshift=6, font=dict(size=11, color='#ff7f0e')
                ))
            # Etiquetas en la base para cada grupo; desplazamiento horizontal para separar
            annotations.append(dict(
                x=per, y=0, xref='x', yref='y', text='Saldo Inicial', showarrow=False,
                yshift=-14, xshift=-30, font=dict(size=10, color='#444')
            ))
            annotations.append(dict(
                x=per, y=0, xref='x', yref='y', text='Saldo Final', showarrow=False,
                yshift=-14, xshift=30, font=dict(size=10, color='#444')
            ))
        fig.update_layout(annotations=annotations)
        return fig

__all__ = ["layout","register"]
