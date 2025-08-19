from __future__ import annotations

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

            # Contexto de datos (resumen agregado) para grounding
            context_text = _build_context_from_df(data_json)

            # Mensajes con memoria (system + resumen de datos + historial + nuevo user)
            messages = [
                {"role":"system","content": _system_prompt()},
                {"role":"system","content": f"Contexto de datos (agregado):\n{context_text}"},
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
