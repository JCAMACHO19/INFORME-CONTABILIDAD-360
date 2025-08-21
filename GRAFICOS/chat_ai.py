from __future__ import annotations

def _build_context_bancos(data_json: str, max_rows: int = 1000) -> str:
    """
    Construye un resumen textual del DataFrame enfocado en BANCO + EMPRESA + PERIODO.
    Este contexto complementa los ya existentes, sin reemplazarlos.

    Permite responder preguntas por:
    - Banco específico (ej: Banco de Occidente, Banco Industrial, etc.)
    - Adiciones y Salidas en un periodo o fecha
    - Variación porcentual de los movimientos respecto al saldo inicial
    - Saldo de Libros y Saldos Iniciales filtrando por banco
    - Siempre omitiendo cuentas que contengan 'CXP'
    """

    if not data_json:
        return "No hay datos bancarios disponibles."
    df = pd.read_json(io.StringIO(data_json), orient='split')

    # Limpieza básica
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if 'Fecha Inicial' in df.columns:
        df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')

    for c in ['Saldo Inicial','Saldo Libros','Movimientos','Adiciones','Salidas']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Omitir cuentas CXP
    if 'Cuenta' in df.columns:
        df = df[~df['Cuenta'].str.contains('CXP', case=False, na=False)]

    if df.empty:
        return "No hay datos bancarios disponibles."

    # Crear periodo YYYY-MM
    df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)

    # Agregar por Periodo + Empresa + Banco
    agg = df.groupby(['Periodo','Empresa','Banco'], as_index=False).agg({
        'Saldo Inicial':'sum',
        'Adiciones':'sum',
        'Salidas':'sum',
        'Movimientos':'sum',
        'Saldo Libros':'sum'
    })

    # Variación (%)
    import numpy as np
    agg['Variacion'] = np.where(
        (agg['Saldo Inicial'] != 0) & (~agg['Saldo Inicial'].isna()),
        (agg['Movimientos'] / agg['Saldo Inicial']) * 100,
        float('nan')
    )

    # Ordenar y limitar filas
    try:
        agg['Periodo_sort'] = pd.to_datetime(agg['Periodo'] + '-01', errors='coerce')
        agg = agg.sort_values('Periodo_sort').drop(columns=['Periodo_sort'])
    except Exception:
        pass
    if len(agg) > max_rows:
        agg = agg.tail(max_rows)

    # Construir texto
    lines = ["Resumen bancario por periodo, empresa y banco (últimos registros):"]
    for _, row in agg.iterrows():
        lines.append(
            f"{row['Periodo']} | {row['Empresa']} | Banco={row['Banco']} | "
            f"SI={row['Saldo Inicial']:.2f} | Adiciones={row['Adiciones']:.2f} | "
            f"Salidas={row['Salidas']:.2f} | MV={row['Movimientos']:.2f} | "
            f"SL={row['Saldo Libros']:.2f} | Var={row['Variacion']:.2f}%"
        )

    return "\n".join(lines)
from dash import dcc, html, Input, Output, State, ctx
import pandas as pd
import io
from pathlib import Path

# Reusar datos y lógica de grafic_time
from grafic_time import cargar_datos

# Cliente OpenAI: asegurar que el paquete 'API' (carpeta hermana) esté en sys.path
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in _sys.path:
    _sys.path.append(str(_ROOT))
from API.API import chat_messages

TAB_ID = 'tab-chat-ai'

# Configuración por defecto del modelo
DEFAULT_MODEL = 'gpt-4o-mini'
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 400

BASE_DIR = Path(__file__).resolve().parent


def layout():
    return html.Div([
        html.H2('Asistente Financiero (IA)'),
        html.P('Haz preguntas en lenguaje natural sobre las métricas de tiempo (Saldo Inicial, Saldo Libros, Movimientos).'),
        dcc.Store(id='ai-conv-store', storage_type='session'),  # memoria de conversación en sesión
        dcc.Store(id='ai-data-store'),  # snapshot de datos en JSON
        html.Div([
            html.Div([
                html.Label('Modelo'),
                dcc.Dropdown(
                    id='ai-model',
                    options=[
                        {'label': 'gpt-4o-mini', 'value': 'gpt-4o-mini'},
                        {'label': 'gpt-4o', 'value': 'gpt-4o'},
                    ], value=DEFAULT_MODEL, clearable=False
                )
            ], style={'minWidth':'220px','marginRight':'10px'}),
            html.Div([
                html.Label('Temperatura'),
                dcc.Slider(id='ai-temp', min=0.0, max=1.5, step=0.1, value=DEFAULT_TEMPERATURE,
                           marks=None, tooltip={'always_visible': False})
            ], style={'flex':1,'minWidth':'220px'}),
        ], style={'display':'flex','flexWrap':'wrap','gap':'10px','alignItems':'center','marginBottom':'10px'}),

        html.Div(id='ai-chat-window', style={
            'border':'1px solid #d0d7de','borderRadius':'8px','padding':'12px','height':'420px',
            'overflowY':'auto','background':'#ffffff'
        }),

        html.Div([
            dcc.Textarea(id='ai-user-input', style={'width':'100%','height':'70px'}, placeholder='Escribe tu pregunta...'),
            html.Div([
                html.Button('Enviar', id='ai-send-btn', n_clicks=0, style={'marginRight':'8px'}),
                html.Button('Limpiar chat', id='ai-clear-btn', n_clicks=0)
            ], style={'marginTop':'6px'})
        ], style={'marginTop':'10px'})
    ], style={'fontFamily':'Arial','padding':'18px'})


def _df_snapshot_json() -> str:
    df = cargar_datos()
    if df.empty:
        df = pd.DataFrame(columns=['Empresa','Fecha','Fecha Inicial','Banco','Saldo Inicial','Saldo Libros','Movimientos'])
    return df.to_json(date_format='iso', orient='split')


def _system_prompt() -> str:
    return (
        "Eres un analista financiero experto. Usa datos de saldos bancarios y movimientos por empresa y periodo. "
        "Responde con explicaciones claras, supuestos explícitos, y si procede, cálculos numéricos resumidos. "
        "Si piden segmentaciones (por empresa, banco, periodo), realiza agregaciones y explica el método. "
        "Cuando estimes valores, indícalo como estimación. Devuelve números con separadores de miles y 2 decimales. "
        "Si te piden series por mes, agrega por periodo YYYY-MM como en el gráfico."
    )


def _build_context_from_df(data_json: str, max_rows: int = 1000) -> str:
    """Construye un resumen textual del DataFrame (agregado básico) para dar contexto a la IA.
    Usamos agregaciones clave para mantener tokens controlados.
    """
    if not data_json:
        return "No hay datos disponibles."
    df = pd.read_json(io.StringIO(data_json), orient='split')
    # Tipos y limpieza
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if 'Fecha Inicial' in df.columns:
        df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
    for c in ['Saldo Inicial','Saldo Libros','Movimientos']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['Fecha'])

    # Agregar por periodo (YYYY-MM) y empresa: totales de libro, inicial y movimientos
    if not df.empty:
        df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)
        agg = df.groupby(['Periodo','Empresa'], as_index=False).agg({
            'Saldo Inicial':'sum','Saldo Libros':'sum','Movimientos':'sum'
        })
        # Top 12 periodos más recientes para reducir tokens
        try:
            agg['Periodo_sort'] = pd.to_datetime(agg['Periodo'] + '-01', errors='coerce')
            agg = agg.sort_values('Periodo_sort').drop(columns=['Periodo_sort'])
        except Exception:
            pass
        if len(agg) > max_rows:
            agg = agg.tail(max_rows)
        # Construir texto
        lines = ["Resumen por periodo y empresa (últimos registros):"]
        for _, row in agg.iterrows():
            lines.append(
                f"{row['Periodo']} | {row['Empresa']} | SI={row['Saldo Inicial']:.2f} | SL={row['Saldo Libros']:.2f} | MV={row['Movimientos']:.2f}"
            )
        return "\n".join(lines)
    return "No hay datos disponibles."


def _build_rich_context_from_df(
    data_json: str,
    max_periods: int = 12,
    top_bancos: int = 6,
    max_lines: int = 1500,
 ) -> str:
    """Construye un resumen avanzado para preguntas por banco, adiciones/salidas,
    variaciones por periodo y totales, omitiendo filas cuya Cuenta contenga 'CXP'.

    Tamaño controlado: limita últimos `max_periods` y top `top_bancos` por SL reciente.
    """
    if not data_json:
        return "Contexto avanzado: no hay datos disponibles."

    df = pd.read_json(io.StringIO(data_json), orient='split')
    if df.empty:
        return "Contexto avanzado: no hay datos disponibles."

    # Tipos
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if 'Fecha Inicial' in df.columns:
        df['Fecha Inicial'] = pd.to_datetime(df['Fecha Inicial'], errors='coerce')
    for c in ['Saldo Inicial','Saldo Libros','Movimientos']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['Fecha'])

    # Omitir CXP si existe la columna Cuenta
    if 'Cuenta' in df.columns:
        df = df[~df['Cuenta'].astype(str).str.contains('CXP', case=False, na=False)]

    if df.empty:
        return "Contexto avanzado: no hay datos (después de filtrar CXP)."

    # Periodo YYYY-MM
    df['Periodo'] = df['Fecha'].dt.to_period('M').astype(str)

    # Adiciones / Salidas por periodo
    pos = df.loc[df['Movimientos'] > 0, ['Periodo','Movimientos']].groupby('Periodo', as_index=True).sum()
    pos = pos.rename(columns={'Movimientos':'Adiciones'})
    neg = df.loc[df['Movimientos'] < 0, ['Periodo','Movimientos']].groupby('Periodo', as_index=True).sum()
    neg = neg.rename(columns={'Movimientos':'Salidas'})

    agg_p = df.groupby('Periodo', as_index=False).agg({
        'Saldo Inicial':'sum', 'Saldo Libros':'sum', 'Movimientos':'sum'
    })
    # Juntar adiciones/salidas
    agg_p = agg_p.set_index('Periodo').join(pos, how='left').join(neg, how='left').fillna(0.0).reset_index()
    # Ajustar salidas (magnitud positiva)
    agg_p['Salidas'] = (-agg_p['Salidas']).clip(lower=0.0)
    # Variaciones
    agg_p['Var_SI_SL'] = agg_p['Saldo Libros'] - agg_p['Saldo Inicial']
    # Orden por periodo y MoM de SL
    try:
        agg_p['_dt'] = pd.to_datetime(agg_p['Periodo'] + '-01', errors='coerce')
        agg_p = agg_p.sort_values('_dt')
        agg_p['Var_MoM_SL'] = agg_p['Saldo Libros'].diff().fillna(0.0)
    except Exception:
        agg_p['Var_MoM_SL'] = 0.0

    # Limitar últimos periodos
    if len(agg_p) > max_periods:
        agg_p_tail = agg_p.tail(max_periods)
    else:
        agg_p_tail = agg_p

    # Totales globales (sobre todo el rango) y SL del último día
    fecha_min = df['Fecha'].min()
    fecha_max = df['Fecha'].max()
    empresas = len(df['Empresa'].dropna().unique()) if 'Empresa' in df.columns else None
    bancos = len(df['Banco'].dropna().unique()) if 'Banco' in df.columns else None

    tot_SI = df['Saldo Inicial'].sum() if 'Saldo Inicial' in df.columns else 0.0
    tot_MV = df['Movimientos'].sum() if 'Movimientos' in df.columns else 0.0
    tot_AD = df.loc[df['Movimientos'] > 0, 'Movimientos'].sum() if 'Movimientos' in df.columns else 0.0
    tot_SAL = -df.loc[df['Movimientos'] < 0, 'Movimientos'].sum() if 'Movimientos' in df.columns else 0.0

    # SL del último periodo (sumando ese corte)
    try:
        last_period = df['Periodo'].iloc[df['Fecha'].argmax()]
        sl_ultimo_global = df.loc[df['Periodo'] == last_period, 'Saldo Libros'].sum()
    except Exception:
        sl_ultimo_global = df['Saldo Libros'].sum() if 'Saldo Libros' in df.columns else 0.0

    # Por banco (top por SL último)
    lines_bancos: list[str] = []
    if 'Banco' in df.columns:
        # SL por banco en último periodo disponible (del banco)
        # Construimos primer y último periodo por banco + SL en esos cortes
        def _bank_sl_at_period(sub: pd.DataFrame, period: str) -> float:
            return sub.loc[sub['Periodo'] == period, 'Saldo Libros'].sum()

        bancos_info = []
        for banco, sub in df.groupby('Banco'):
            sub = sub.sort_values('Fecha')
            p_first = sub['Periodo'].iloc[0]
            p_last = sub['Periodo'].iloc[-1]
            sl_first = _bank_sl_at_period(sub, p_first)
            sl_last = _bank_sl_at_period(sub, p_last)
            mv_sum = sub['Movimientos'].sum()
            si_sum = sub['Saldo Inicial'].sum()
            ad_sum = sub.loc[sub['Movimientos'] > 0, 'Movimientos'].sum()
            sal_sum = -sub.loc[sub['Movimientos'] < 0, 'Movimientos'].sum()
            bancos_info.append({
                'Banco': banco,
                'SL_ultimo': sl_last,
                'SL_primero': sl_first,
                'Periodo_primero': p_first,
                'Periodo_ultimo': p_last,
                'SI_total': si_sum,
                'MV_total': mv_sum,
                'AD_total': ad_sum,
                'SAL_total': sal_sum,
                'Var_SL_total': sl_last - sl_first,
            })

        bancos_df = pd.DataFrame(bancos_info)
        bancos_df = bancos_df.sort_values('SL_ultimo', ascending=False)
        bancos_df_top = bancos_df.head(top_bancos)

        for _, row in bancos_df_top.iterrows():
            lines_bancos.append(
                f"{row['Banco']}: SI_total={row['SI_total']:.2f} | MV_total={row['MV_total']:.2f} "
                f"(AD={row['AD_total']:.2f}, SAL={row['SAL_total']:.2f}) | SL_último={row['SL_ultimo']:.2f} "
                f"| Var_SL_total={row['Var_SL_total']:.2f} [{row['Periodo_primero']} -> {row['Periodo_ultimo']}]"
            )

    # Construcción del texto final
    lines: list[str] = []
    lines.append("Contexto avanzado (agregado adicional):")
    # Totales globales
    lines.append(
        (
            f"Global | Fecha: {fecha_min.date() if pd.notna(fecha_min) else 'N/A'} a {fecha_max.date() if pd.notna(fecha_max) else 'N/A'} | "
            f"Empresas: {empresas if empresas is not None else 'N/A'} | Bancos: {bancos if bancos is not None else 'N/A'}\n"
            f"Totales -> SI={tot_SI:.2f} | MV={tot_MV:.2f} (AD={tot_AD:.2f}, SAL={tot_SAL:.2f}) | SL_último={sl_ultimo_global:.2f}"
        )
    )

    # Serie por periodo (últimos N)
    lines.append("Serie por periodo (últimos registros):")
    for _, r in agg_p_tail.iterrows():
        lines.append(
            f"{r['Periodo']} | SI={r['Saldo Inicial']:.2f} | MV={r['Movimientos']:.2f} (AD={r['Adiciones']:.2f}, SAL={r['Salidas']:.2f}) | "
            f"SL={r['Saldo Libros']:.2f} | Var(SI->SL)={r['Var_SI_SL']:.2f} | VarMoM(SL)={r['Var_MoM_SL']:.2f}"
        )

    # Resumen por banco (Top)
    if lines_bancos:
        lines.append("Bancos (top por SL último):")
        lines.extend(lines_bancos)

    # Control de tamaño final
    if len(lines) > max_lines:
        lines = lines[-max_lines:]

    return "\n".join(lines)


def register(app):
    # Snapshot inicial de datos al cargar la pestaña
    @app.callback(
        Output('ai-data-store','data'),
        Input('tab-content','children'),
        prevent_initial_call=False
    )
    def _snapshot_on_tab(_):
        return _df_snapshot_json()

    # Chat: limpiar o enviar en un solo callback (evita salidas duplicadas)
    @app.callback(
        Output('ai-conv-store','data'),
        Input('ai-send-btn','n_clicks'),
        Input('ai-clear-btn','n_clicks'),
        State('ai-user-input','value'),
        State('ai-conv-store','data'),
        State('ai-data-store','data'),
        State('ai-model','value'),
        State('ai-temp','value'),
        prevent_initial_call=True
    )
    def _chat(send_clicks, clear_clicks, user_text, conv, data_json, model, temp):
        trig = ctx.triggered_id if ctx else None
        conv = conv or []

        # Limpiar conversación
        if trig == 'ai-clear-btn':
            return []

        # Enviar mensaje
        if trig == 'ai-send-btn':
            user_text = (user_text or '').strip()
            if not user_text:
                return conv

            # Contextos de datos (resúmenes agregados) para grounding
            context_text = _build_context_from_df(data_json)
            context_text_adv = _build_rich_context_from_df(data_json)
            context_text_bancos = _build_context_bancos(data_json)

            # Mensajes con memoria (system + resumen de datos + historial + nuevo user)
            messages = [
                {"role":"system","content": _system_prompt()},
                {"role":"system","content": f"Contexto de datos (agregado):\n{context_text}"},
                {"role":"system","content": f"Contexto de datos (agregado avanzado):\n{context_text_adv}"},
                {"role":"system","content": f"Contexto bancario detallado (por banco, empresa y periodo):\n{context_text_bancos}"},
            ]
            history = conv[-8:]
            for m in history:
                messages.append(m)
            messages.append({"role":"user","content": user_text})

            resp = chat_messages(
                messages=messages,
                model=model or DEFAULT_MODEL,
                temperature=float(temp or DEFAULT_TEMPERATURE),
                max_tokens=DEFAULT_MAX_TOKENS,
            )
            choice = resp.choices[0] if getattr(resp, 'choices', None) else None
            ai_text = choice.message.content if choice and getattr(choice, 'message', None) else ''

            return conv + [
                {"role":"user","content": user_text},
                {"role":"assistant","content": ai_text}
            ]

        # Sin disparador válido
        return conv

    # Render del chat
    @app.callback(
        Output('ai-chat-window','children'),
        Input('ai-conv-store','data'),
        prevent_initial_call=False
    )
    def _render(conv):
        conv = conv or []
        if not conv:
            return html.Div("No hay mensajes aún. Escribe tu pregunta.", style={'color':'#666'})
        items = []
        for m in conv:
            is_user = (m.get('role') == 'user')
            bubble_style = {
                'maxWidth':'85%', 'margin':'6px 0', 'padding':'8px 10px', 'borderRadius':'10px',
                'background': '#e9f2ff' if is_user else '#f6f8fa', 'border':'1px solid #d0d7de'
            }
            items.append(html.Div([
                html.Div('Tú' if is_user else 'Asistente', style={'fontWeight':'bold','fontSize':'12px','color':'#57606a'}),
                html.Div(m.get('content',''), style={'whiteSpace':'pre-wrap'})
            ], style={**bubble_style, 'alignSelf': 'flex-end' if is_user else 'flex-start'}))
        return html.Div(items, style={'display':'flex','flexDirection':'column'})

__all__ = ['layout','register']
