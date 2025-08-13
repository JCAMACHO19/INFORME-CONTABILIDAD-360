from dash import Dash, dcc, html, Input, Output
import grafic_bancos
import cuadro_banc

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = 'Dashboard Bancos'

TAB_CONTENT = {
    'tab-grafica-bancos': grafic_bancos,
    'tab-cuadro-bancos': cuadro_banc
}

def main_layout():
    return html.Div([
        html.H1('Dashboard Bancos', style={'fontFamily':'Arial'}),
        dcc.Tabs(id='tabs', value='tab-grafica-bancos', children=[
            dcc.Tab(label='Gráfica Bancos', value='tab-grafica-bancos'),
            dcc.Tab(label='Cuadro Bancos', value='tab-cuadro-bancos'),
        ]),
        html.Div(id='tab-content')
    ], style={'padding':'10px','fontFamily':'Arial'})

app.layout = main_layout

@app.callback(Output('tab-content','children'), Input('tabs','value'))
def render_tab(tab_value):
    module = TAB_CONTENT.get(tab_value)
    if not module:
        return html.Div('Tab no encontrada')
    return module.layout()

# Registrar callbacks de ambos módulos
grafic_bancos.register(app)
cuadro_banc.register(app)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
