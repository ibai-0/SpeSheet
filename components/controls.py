from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from prepare_data import df_totals, min_year, max_year

def layout():
    return html.Div(id='year-controls-container', children=[
        dbc.Card([
            dbc.CardBody([
                html.Label("Select Year:", className="fw-bold mb-1 small"),
                dcc.Slider(
                    id='year-slider',
                    min=min_year,
                    max=max_year,
                    value=max_year,
                    marks={str(y): {'label': str(y), 'style': {'color': '#7f8c8d', 'fontSize': '0.7rem'}} 
                           for y in range(min_year, max_year + 1, 10)},
                    step=1,
                ),
                html.Div([
                    dbc.Button("▶ Play", id="play-button", n_clicks=1, color="primary", className="me-2", size="sm"),
                ], className="mt-1"),
            ])
        ], className="shadow-sm mb-2"),
        dcc.Interval(
            id='auto-stepper',
            interval=800, # year advance ms
            n_intervals=0,
            disabled=True
        ),
    ])

## Year slider animation
@callback(
    Output('year-slider', 'value'),
    Input('auto-stepper', 'n_intervals'),
    State('year-slider', 'value'),
    State('year-slider', 'max'),
    State('year-slider', 'min'),
    prevent_initial_call=True
)
def animate_slider(n, current_year, max_y, min_y):
    return current_year + 1 if current_year < max_y else min_y

## Play Stop toggle
@callback(
    Output('auto-stepper', 'disabled'),
    Output('play-button', 'children'),
    Input('play-button', 'n_clicks'),
    State('auto-stepper', 'disabled')
)
def toggle_play(n, is_disabled):
    if n % 2 == 0:
        return True, "▶ Play"
    return False, "⏸ Pause"

## Statistics cards update
@callback(
    Output('stats-container', 'children'),
    Input('year-slider', 'value')
)
def update_stats(selected_year):
    if selected_year is None:
        return []
    dff = df_totals[df_totals['Year'] == selected_year]
    if dff.empty:
        return []
    global_sum = dff['Value'].sum()
    max_row = dff.loc[dff['Value'].idxmax()]
    
    return [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Global Emissions", className="card-subtitle text-muted small"),
            html.H5(f"{global_sum:,.1f} Mt CO2", className="text-primary mb-0")
        ], className="py-2"), className="border-start border-primary border-4"), width=4),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Top Emitter", className="card-subtitle text-muted small"),
            html.H5(f"{max_row['Country']}", className="text-danger mb-0")
        ], className="py-2"), className="border-start border-danger border-4"), width=4),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Nation Average", className="card-subtitle text-muted small"),
            html.H5(f"{dff['Value'].mean():,.2f} Mt", className="text-success mb-0")
        ], className="py-2"), className="border-start border-success border-4"), width=4)
    ]
