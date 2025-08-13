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
                    offsetgroup='libros',
                    legendgroup=f"{emp}-libros",
                    hovertemplate='Periodo: %{x}<br>Empresa: %{fullData.name}<br>Saldo Libros: %{y:,.2f}<extra></extra>'
                )
        # Línea: Movimientos total por periodo de Fecha
        dfl = df.groupby('PeriodoLib', as_index=False).agg({'Movimientos':'sum'})
        # Asegurar que los periodos de la línea estén presentes en el orden del eje X
        if not dfl.empty:
            cats = sorted(set(cats).union(set(dfl['PeriodoLib'].dropna().unique())))
        fig.add_trace(go.Scatter(x=dfl['PeriodoLib'], y=dfl['Movimientos'], name='Movimientos', mode='lines+markers',
                                 line=dict(color='#2ca02c', width=2)))
        # Layout: dos pilas apiladas lado a lado por periodo (via offsetgroup)
        fig.update_layout(barmode='stack',
                          title='Saldo Libros vs Saldo Inicial por periodo (apilados por Empresa), y Movimientos mensual',
                          xaxis_title='Periodo (YYYY-MM)', yaxis_title='Valor', legend_title='Serie',
                          plot_bgcolor='#ffffff', paper_bgcolor='#fafbfc',
                          font=dict(family='Arial', size=12, color='#222'),
                          hovermode='x unified')
        fig.update_xaxes(showgrid=False, linecolor='#d0d7de', type='category',
                         categoryorder='array', categoryarray=cats)
        fig.update_yaxes(showgrid=True, gridcolor='#eef2f5', zerolinecolor='#d0d7de')
        return fig

__all__ = ["layout","register"]
