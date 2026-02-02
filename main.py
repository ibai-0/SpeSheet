import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
from prepare_data import min_year, max_year
import charts 

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    # Título Principal
    dbc.Row([
        dbc.Col(html.H1("ALLSTAT: CO2 Emissions Dashboard", 
                        className="text-center mt-4 mb-2", 
                        style={'color': '#2c3e50', 'fontWeight': 'bold'}), width=12),
        dbc.Col(html.P("Análisis avanzado de datos spatio-temporal para estadísticas oficiales", 
                        className="text-center text-muted mb-4"), width=12),
    ]),

    # Barra de Estadísticas - Requirement 2.1 & 2.2
    # El ID 'stats-container' será llenado por el callback en charts.py
    dbc.Row(id='stats-container', className="mb-4"),

    # Sección de Tabs
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label='Emissions Map', tab_id='tab-1'),
                dbc.Tab(label='Sector Breakdown', tab_id='tab-2'),
                dbc.Tab(label='Per Capita Rank', tab_id='tab-3'),
                dbc.Tab(label='Data Explorer', tab_id='tab-4'),
            ], id="tabs", active_tab='tab-1', className="mb-3"),
        ], width=12)
    ]),

    # Control de Tiempo y Visualización
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Seleccionar Año:", className="fw-bold mb-2"),
                    dcc.Slider(
                        id='year-slider',
                        min=min_year,
                        max=max_year,
                        value=max_year,
                        marks={str(y): {'label': str(y), 'style': {'color': '#7f8c8d'}} 
                               for y in range(min_year, max_year + 1, 10)},
                        step=1,
                    ),
                    html.Div(id='tabs-content', className="mt-4")
                ])
            ], className="shadow-sm") # Añade una sombra sutil para profundidad
        ], width=12)
    ]),

    # En main.py, dentro del layout, justo antes del Footer:
    dcc.Interval(
        id='auto-stepper',
        interval=1500,  # 1.5 segundos por año para que sea fluido pero legible
        n_intervals=0,
        disabled=True   # Empieza apagado
    ),

    # Añade un botón debajo del slider para controlar el flujo
    dbc.Button("▶ Reproducir Histórico", id="play-button", n_clicks=0, color="primary", className="mt-2"),


    # Pie de página con créditos del grupo
    html.Footer(
        dbc.Row(
            dbc.Col(html.P("© 2026 Grupo de Innovación de Datos - Proyecto ALLSTAT", 
                           className="text-center mt-5 text-secondary small"))
        )
    )
], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

if __name__ == '__main__':
    app.run(debug=True)

