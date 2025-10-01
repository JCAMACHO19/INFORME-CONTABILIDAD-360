from dash import Dash, dcc, html, Input, Output
import grafic_bancos
import cuadro_banc
import bancos_por_empresa
from grafic_time import layout as layout_time, register as register_time
from chat_ai import layout as layout_chat, register as register_chat

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = 'Dashboard Bancos'

TAB_CONTENT = {
    'tab-grafica-bancos': grafic_bancos,
    'tab-cuadro-bancos': cuadro_banc
}

def main_layout():
    return html.Div([
        # Título visible con presencia y fondo morado elegante, ligeramente transparente
        html.H1(
            'Dashboard Bancos',
            style={
                # Familia de fuente: preferir Coolvetica (requiere archivo en assets/fonts)
                'fontFamily': "'Coolvetica','Montserrat','Helvetica Neue','Arial',sans-serif",
                'color': '#000',
                'textAlign': 'center',
                # Tamaño adaptable que luce bien en desktop y se ajusta en pantallas más pequeñas
                'fontSize': 'clamp(24px, 3.3vw, 40px)',
                'fontWeight': 600,
                # Morado/índigo basado en la paleta usada en grafic_time (#31356D), con transparencia suave
                'background': 'rgba(49, 53, 109, 0.18)',
                'padding': '14px 20px',
                'margin': '0 0 12px 0',
                'borderRadius': '12px',
                'letterSpacing': '0.5px',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.06)'
            }
        ),
        dcc.Tabs(id='tabs', value='tab-grafica-bancos', children=[
            dcc.Tab(label='Gráfica Bancos', value='tab-grafica-bancos'),
            dcc.Tab(label='Cuadro Bancos', value='tab-cuadro-bancos'),
            dcc.Tab(label='Bancos por Empresa', value='tab-bancos-empresa'),
            dcc.Tab(label='Evolución Tiempo', value='tab-time'),
            dcc.Tab(label='Chat IA', value='tab-chat')
        ]),
        html.Div(id='tab-content')
    ], style={'padding':'10px','fontFamily':'Arial'})

app.layout = main_layout

@app.callback(Output('tab-content','children'), Input('tabs','value'))
def render_tab(tab_value):
    if tab_value == 'tab-grafica-bancos':
        return grafic_bancos.layout()
    elif tab_value == 'tab-cuadro-bancos':
        return cuadro_banc.layout()
    elif tab_value == 'tab-bancos-empresa':
        return bancos_por_empresa.layout()
    elif tab_value == 'tab-time':
        return layout_time()
    elif tab_value == 'tab-chat':
        return layout_chat()
    return html.Div('Tab no encontrada')

# Registrar callbacks de ambos módulos
grafic_bancos.register(app)
cuadro_banc.register(app)
bancos_por_empresa.register(app)
register_time(app)
register_chat(app)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
