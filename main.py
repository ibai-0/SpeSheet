import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, callback
from prepare_data import min_year, max_year
import charts 

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

app.layout = dbc.Container([

    ## Title
    dbc.Row([
        dbc.Col(html.H1("ALLSTAT: CO2 Emissions Dashboard", className="text-center mt-2 mb-1", style={'color': '#2c3e50', 'fontWeight': 'bold'}), width=12),
        dbc.Col(html.P("Advanced spatio-temporal data analysis for official statistics", 
                        className="text-center text-muted mb-3 small"), width=12),
    ]),

    # Tab Section
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label='Emissions Map', tab_id='tab-1'),
                dbc.Tab(label='Nation Prosperity', tab_id='tab-2'),
                dbc.Tab(label='Correlation Emission Prosperity', tab_id='tab-3'),
            ], id="tabs", active_tab='tab-1', className="mb-2 nav-justified"),
        ], width=12)
    ]),

    # Controls and Visualization
    dbc.Row([
        dbc.Col([
            html.Div(id='tabs-content', className="mt-2")
        ], width=12)
    ]),

    # Dynamics Conclusion Section (Updates based on active tab)
    dbc.Row([
        dbc.Col(html.Div(id='tab-conclusion-container', className="mt-4 mb-2"), width=12)
    ]),

    # Pie de página con créditos del grupo
    html.Footer(
        dbc.Row(
            dbc.Col(html.P("© 2026 Ibai Mayoral - Hugo Recio - Iñaki Morengo - Xabier Aranguena", 
                        className="text-center mt-5 text-secondary small"))
        )
    )
], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

@callback(
    Output('tab-conclusion-container', 'children'),
    Input('tabs', 'active_tab')
)
def update_tab_conclusion(active_tab):
    """
    Renders a professional analytical summary for each tab.
    """
    conclusions = {
        'tab-1': "Chavales os toca hacer conclusiones",
        'tab-2': "Chavales os toca hacer conclusiones",
        'tab-3': "Chavales os toca hacer conclusiones",
    }
    
    insight_text = conclusions.get(active_tab, "Explore the data to extract meaningful patterns.")
    
    return dbc.Card(dbc.CardBody([
        html.H6([
            html.I(className="bi bi-lightbulb-fill me-2"),
            "Key Research Insight"
        ], className="text-primary fw-bold mb-2"),
        html.P(insight_text, className="mb-0 text-dark fst-italic")
    ]), className="shadow-sm border-0", style={'backgroundColor': '#eef2f7'})


if __name__ == '__main__':
    app.run(debug=True)

