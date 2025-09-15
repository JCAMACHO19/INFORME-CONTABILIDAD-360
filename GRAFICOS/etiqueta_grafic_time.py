from __future__ import annotations

from typing import Optional, List
import io
import pandas as pd
from dash import dcc, html, Input, Output
import plotly.graph_objects as go


def layout():
    container_style = {
        'minWidth': '380px',
        'maxWidth': '520px',
        'flex': '0 1 460px',
        'padding': '12px 16px 16px 16px',
        'background': 'linear-gradient(145deg, #ffffff, #f5f7fa)',
        'border': '1px solid #e2e8f0',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(30,41,59,0.06), 0 1px 2px rgba(30,41,59,0.04)',
        'fontFamily': '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", Arial, sans-serif'
    }
    panel_style = {'flex': '1', 'minWidth': '320px', 'background': '#ffffff', 'padding': '8px 10px 4px', 'border': '1px solid #e5e9ef', 'borderRadius': '8px'}
    header_style = {'fontWeight': 600, 'marginBottom': '4px', 'fontSize': '12px', 'letterSpacing': '.5px', 'textTransform': 'uppercase', 'color': '#475569'}
    return html.Div(
        [
            html.H4('Radar de Banco', style={'margin': '0 0 12px', 'fontWeight': 600, 'fontSize': '16px', 'color': '#1e293b'}),
            html.Div([
                html.Div([
                    html.Div('Saldo Inicial', style=header_style),
                    dcc.Graph(id='gt-radar-inicial', style={'height': '290px'}),
                ], style=panel_style),
                html.Div([
                    html.Div('Saldo Libros', style=header_style),
                    dcc.Graph(id='gt-radar-libros', style={'height': '290px'}),
                ], style=panel_style),
            ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '14px'}),
        ],
        style=container_style
    )


def _periodo_str_es(periodo: str) -> str:
    try:
        yy, mm = str(periodo).split('-')[:2]
        meses_es = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril', '05': 'Mayo', '06': 'Junio',
            '07': 'Julio', '08': 'Agosto', '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        return f"{meses_es.get(mm.zfill(2), mm)} {yy}"
    except Exception:
        return str(periodo)


def _empty_polar(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=msg, font=dict(size=12, color='#334155', family='Inter,Arial,sans-serif')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#ffffff',
        polar=dict(
            # Fondo gris muy claro para contraste suave
            bgcolor='rgba(243,244,246,0.75)',  # #f3f4f6 translúcido
            radialaxis=dict(visible=True, range=[0, 1], gridcolor='#edf2f7', gridwidth=1, linecolor='#cbd5e1'),
            angularaxis=dict(gridcolor='#f1f5f9')
        ),
        margin=dict(l=18, r=18, t=46, b=22),
        showlegend=False,
        font=dict(family='Inter,Arial,sans-serif', color='#334155')
    )
    return fig


def _radar(
    title: str,
    categorias: List[str],
    valores: List[float],
    color: str,
    ticktexts: Optional[List[str]] = None,
    radial_max: Optional[float] = None,
    radial_tickvals: Optional[List[float]] = None,
    radial_ticktext: Optional[List[str]] = None,
) -> go.Figure:
    if not categorias or not valores or sum(abs(v) for v in valores) == 0:
        return _empty_polar(title)
    # Cerrar el polígono
    theta = categorias + [categorias[0]]
    r = valores + [valores[0]]
    max_val = max(v for v in valores if v is not None)
    max_val = max_val if max_val > 0 else 1.0
    if radial_max is not None and radial_max > 0:
        max_val = float(radial_max)
    fig = go.Figure()
    def _hex_to_rgba(c: str, alpha: float = 0.2) -> str:
        try:
            if isinstance(c, str) and c.startswith('#') and len(c) == 7:
                r = int(c[1:3], 16)
                g = int(c[3:5], 16)
                b = int(c[5:7], 16)
                return f'rgba({r},{g},{b},{alpha})'
            if isinstance(c, str) and c.startswith('rgb('):
                inner = c[4:-1]
                parts = [p.strip() for p in inner.split(',')]
                if len(parts) == 3:
                    r, g, b = parts
                    return f'rgba({r},{g},{b},{alpha})'
            if isinstance(c, str) and c.startswith('rgba('):
                return c
        except Exception:
            pass
        return c
    fig.add_trace(go.Scatterpolar(
        r=r,
        theta=theta,
        fill='toself',
        name=title,
        line=dict(color=color, width=2),
        fillcolor=_hex_to_rgba(color, 0.18),
        marker=dict(size=5, color=color, line=dict(color='#ffffff', width=1)),
        hovertemplate='<b>%{theta}</b><br>Valor: %{r:,.2f}<extra></extra>'
    ))
    # Ángulo del eje radial (donde se ubican las etiquetas de referencia)
    radial_axis_angle = 90

    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color='#334155', family='Inter,Arial,sans-serif')),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#ffffff',
        polar=dict(
            # Fondo gris muy claro para contraste suave
            bgcolor='rgba(243,244,246,0.75)',  # #f3f4f6 translúcido
            radialaxis=dict(
                visible=True,
                range=[0, max_val * 1.05],
                gridcolor='#e2e8f0',
                gridwidth=1,
                tickfont=dict(size=10, color='#64748b'),
                angle=radial_axis_angle,
                showline=True,
                linecolor='#cbd5e1',
                ticks='',
                showticklabels=False,
                **({'tickmode': 'array', 'tickvals': radial_tickvals, 'ticktext': radial_ticktext} if radial_tickvals and radial_ticktext else {})
            ),
            angularaxis=dict(
                gridcolor='#f1f5f9',
                linecolor='#e2e8f0',
                tickfont=dict(size=11, color='#475569'),
                rotation=90,  # alinear primer eje arriba para simetría
                direction='clockwise',
                **({'tickmode': 'array', 'tickvals': categorias, 'ticktext': ticktexts} if ticktexts else {})
            )
        ),
        margin=dict(l=18, r=18, t=46, b=22),
        font=dict(family='Inter,Arial,sans-serif', color='#334155')
    )

    # Etiquetas personalizadas horizontales en la línea de referencia (misma posición que los ticks)
    if radial_tickvals:
        import math

        def _nice_label(v: float) -> str:
            try:
                av = abs(v)
                suffix = ''
                n = v
                if av >= 1_000_000:
                    n = v / 1_000_000.0
                    suffix = ' M'
                elif av >= 1_000:
                    n = v / 1_000.0
                    suffix = ' k'
                else:
                    n = v

                if n == 0:
                    return '0' + suffix

                an = abs(n)
                # Redondear a 2 cifras significativas "bonitas"
                order = math.floor(math.log10(an)) if an > 0 else 0
                pow10 = 10 ** max(order - 1, -3)  # permite decimales para valores pequeños
                rounded = round(n / pow10) * pow10

                # Formateo: evitar decimales cuando sea posible
                if pow10 >= 1:
                    txt = f"{int(rounded)}{suffix}"
                else:
                    txt = f"{rounded:.1f}{suffix}"
                    if '.' in txt:
                        txt = txt.rstrip('0').rstrip('.')
                return txt.replace('.', ',')
            except Exception:
                return str(v)

        custom_labels = [_nice_label(v) for v in radial_tickvals]

        fig.add_trace(
            go.Scatterpolar(
                r=radial_tickvals,
                theta=[radial_axis_angle] * len(radial_tickvals),
                mode='text',
                text=custom_labels,
                textfont=dict(size=10, color='#64748b'),
                textposition='middle right',
                cliponaxis=False,
                showlegend=False,
                hoverinfo='skip'
            )
        )
    return fig


def register(app):
    @app.callback(
        Output('gt-radar-inicial', 'figure'),
        Output('gt-radar-libros', 'figure'),
        Input('grafico-time', 'hoverData'),
        Input('gt-data', 'data'),
        Input('gt-empresa-dropdown', 'value'),
        Input('gt-banco-dropdown', 'value'),
    )
    def actualizar_radars(hoverData, data_json: Optional[str], empresas_sel, bancos_sel):
        if not data_json:
            return _empty_polar('Sin datos'), _empty_polar('Sin datos')

        # Reconstruir DF como en grafic_time
        df = pd.read_json(io.StringIO(data_json), orient='split')
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        if 'Fecha Inicial' in df.columns:
            df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
        for c in ['Saldo Libros', 'Saldo Inicial', 'Movimientos']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['Fecha'])

        # Filtros por dropdown (igual que en grafic_time)
        if empresas_sel:
            df = df[df['Empresa'].isin(empresas_sel)]
        if bancos_sel and 'Banco' in df.columns:
            df = df[df['Banco'].isin(bancos_sel)]
        if df.empty:
            return _empty_polar('Sin datos tras filtros'), _empty_polar('Sin datos tras filtros')

        # Construir periodos
        df['PeriodoLib'] = df['Fecha'].dt.to_period('M').astype(str)
        if 'Fecha Inicial' in df.columns:
            df['PeriodoIni'] = df['Fecha Inicial'].dt.to_period('M').astype(str)

        # Determinar periodo a partir del hover (x)
        periodo_sel = None
        try:
            if hoverData and 'points' in hoverData and hoverData['points']:
                periodo_sel = hoverData['points'][0].get('x')
        except Exception:
            periodo_sel = None

        # Fallback: usar último periodo disponible
        if not periodo_sel:
            cats = set(df['PeriodoLib'].dropna().unique()) if 'PeriodoLib' in df.columns else set()
            if 'PeriodoIni' in df.columns:
                cats = cats.union(set(df['PeriodoIni'].dropna().unique()))
            if not cats:
                return _empty_polar('Sin datos'), _empty_polar('Sin datos')
            periodo_sel = sorted(cats)[-1]

        # AGRUPACIONES por banco siguiendo la misma lógica del gráfico madre
        # Inicial: primer día por Empresa/Banco/PeriodoIni
        ini_por_banco = pd.Series(dtype=float)
        if 'PeriodoIni' in df.columns and 'Saldo Inicial' in df.columns:
            dfi = df.dropna(subset=['PeriodoIni', 'Fecha Inicial']).copy()
            dfi = dfi[dfi['PeriodoIni'] == periodo_sel]
            if not dfi.empty:
                min_dates = dfi.groupby(['Empresa', 'Banco', 'PeriodoIni'])['Fecha Inicial'].transform('min')
                dfi_firstday = dfi[dfi['Fecha Inicial'] == min_dates]
                ini_por_banco = dfi_firstday.groupby('Banco')['Saldo Inicial'].sum()

        # Libros: último día por Empresa/Banco/PeriodoLib
        lib_por_banco = pd.Series(dtype=float)
        if 'Saldo Libros' in df.columns:
            dfl = df.dropna(subset=['PeriodoLib', 'Fecha']).copy()
            dfl = dfl[dfl['PeriodoLib'] == periodo_sel]
            if not dfl.empty:
                max_dates = dfl.groupby(['Empresa', 'Banco', 'PeriodoLib'])['Fecha'].transform('max')
                dfl_lastday = dfl[dfl['Fecha'] == max_dates]
                lib_por_banco = dfl_lastday.groupby('Banco')['Saldo Libros'].sum()

        # Preparar ejes del radar (bancos) y valores en el mismo orden
        bancos_cats = sorted(set(ini_por_banco.index).union(set(lib_por_banco.index)))

        # Envolver etiquetas largas para evitar cortes en el eje angular
        def wrap_label(s: str, width: int = 14) -> str:
            try:
                s = str(s)
                if len(s) <= width:
                    return s
                # Intentar cortar en el espacio más cercano antes del límite
                parts = []
                current = s
                while len(current) > width:
                    cut = current.rfind(' ', 0, width)
                    if cut == -1:
                        cut = width
                    parts.append(current[:cut])
                    current = current[cut:].lstrip()
                if current:
                    parts.append(current)
                return '<br>'.join(parts)
            except Exception:
                return s

        bancos_ticktext = [wrap_label(b) for b in bancos_cats]
        vals_ini = [float(ini_por_banco.get(b, 0.0)) for b in bancos_cats]
        vals_lib = [float(lib_por_banco.get(b, 0.0)) for b in bancos_cats]

        # Calcular máximo compartido para sincronizar la escala entre ambos radars
        try:
            local_max_ini = max(vals_ini) if vals_ini else 0.0
            local_max_lib = max(vals_lib) if vals_lib else 0.0
            shared_max = max(local_max_ini, local_max_lib)
            if not (shared_max and shared_max > 0):
                shared_max = 1.0
        except Exception:
            shared_max = 1.0

        # Definir 3 ticks uniformes (1/3, 2/3 y 1x) y sus etiquetas
        tick1 = shared_max / 3.0
        tick2 = shared_max * 2.0 / 3.0
        tick3 = shared_max

        def fmt_val(v: float) -> str:
            try:
                if abs(v) >= 1_000_000:
                    return f"{v/1_000_000:.1f} M".replace('.', ',')
                if abs(v) >= 1_000:
                    return f"{v/1_000:.1f} k".replace('.', ',')
                return f"{v:.0f}".replace('.', ',')
            except Exception:
                return str(v)

        radial_tickvals = [tick1, tick2, tick3]
        radial_ticktext = [fmt_val(tick1), fmt_val(tick2), fmt_val(tick3)]

        per_title = _periodo_str_es(periodo_sel)
        # Títulos internos sin los prefijos "Saldo Inicial" / "Saldo Libros", sólo periodo
        fig_ini = _radar(
            f"{per_title}",
            bancos_cats,
            vals_ini,
            '#1f77b4',
            bancos_ticktext,
            radial_max=shared_max,
            radial_tickvals=radial_tickvals,
            radial_ticktext=radial_ticktext,
        )
        fig_lib = _radar(
            f"{per_title}",
            bancos_cats,
            vals_lib,
            '#ff7f0e',
            bancos_ticktext,
            radial_max=shared_max,
            radial_tickvals=radial_tickvals,
            radial_ticktext=radial_ticktext,
        )
        return fig_ini, fig_lib


__all__ = ["layout", "register"]
