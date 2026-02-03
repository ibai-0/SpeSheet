from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from prepare_data import df_totals, df_capita, df_sectors
from components import controls

def layout():
    return html.Div(className='tab-animacion', children=[
        controls.layout(),
        dbc.Row(id='stats-container', className="mb-3 g-2"),
        dbc.Row([
            # Left Column - Map
            dbc.Col([
                dcc.Graph(id='map-graph')
            ], width=8),
            
            # Right Column - Side Plots & Controls
            dbc.Col([
                html.Div(id='subplots-container'),
                dbc.Button("Advanced Analysis", id="open-advanced", color="primary", className="w-100 shadow-sm mt-1", size="sm"),
            ], width=4)
        ]),
        
        # Unified Modal for additional analysis
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Advanced Global Analysis")),
            dbc.ModalBody([
                html.Div(id="modal-advanced-body"),
                html.Hr(className="my-2"),
                dbc.Button("Close Analysis", id="close-advanced", color="secondary", className="float-end btn-sm mb-2"),
            ]),
        ], id="modal-advanced", size="xl", is_open=False),
        
        # Global Store for country selection
        dcc.Store(id='selected-country-store', data=None),
    ])


## MAPA
@callback(
    Output('map-graph', 'figure'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value')
)
def update_map(tab, selected_year):
    if tab != 'tab-1' or selected_year is None:
        return go.Figure()
    
    dff = df_totals[df_totals['Year'] == selected_year]
    fig_map = px.choropleth(
        dff, locations="ISOcode", color="Value", hover_name="Country",
        color_continuous_scale="Viridis", height=380
    )
    fig_map.update_layout(
        margin={"r":0,"t":25,"l":0,"b":0}, 
        transition_duration=100,
        coloraxis_colorbar=dict(title="CO2 (Mt)", thickness=15, len=0.8)
    )
    return fig_map

@callback(
    Output('selected-country-store', 'data'),
    Input('map-graph', 'clickData'),
    Input('reset-global-btn', 'n_clicks'),
    prevent_initial_call=False
)
def update_country_store(clickData, n_clicks):
    if ctx.triggered_id == 'reset-global-btn':
        return None
    if clickData and 'points' in clickData:
        return clickData['points'][0]['hovertext']
    return None

## SUBPLOTS


@callback(
    Output('subplots-container', 'children'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value'),
    Input('selected-country-store', 'data')
)
def update_subplots(tab, selected_year, country_selected):
    if tab != 'tab-1' or selected_year is None:
        return None

    # 1. Historical CO2 per capita
    if country_selected:
        df_hist_capita = df_capita[df_capita['Country'] == country_selected]
        title_hist = f'Historical CO2 per Capita: {country_selected}'
    else:
        df_hist_capita = df_capita.groupby('Year')['Value'].mean().reset_index()
        title_hist = 'Historical CO2 per Capita (Global Average)'
        
    if df_hist_capita.empty:
        fig_historic_capita = go.Figure().update_layout(title="No data available")
    else:
        fig_historic_capita = px.line(
            df_hist_capita, x='Year', y='Value', 
            title=title_hist,
            template='plotly_white'
        )
        fig_historic_capita.add_vline(x=selected_year, line_dash="dash", line_color="red")
    fig_historic_capita.update_layout(
        margin={"r":5,"t":30,"l":5,"b":5}, 
        height=210,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    # 2. Sector Breakdown
    if country_selected:
        df_s_year = df_sectors[(df_sectors['Year'] == selected_year) & (df_sectors['Country'] == country_selected)]
        title_pie = f'Sectors in {country_selected}'
    else:
        df_s_year = df_sectors[df_sectors['Year'] == selected_year]
        df_s_year = df_s_year.groupby('Sector')['Value'].sum().reset_index()
        title_pie = f'Emissions by Sector (Global)'

    if df_s_year.empty:
        fig_sector_pie = go.Figure().update_layout(title="No data available")
    else:
        fig_sector_pie = px.pie(
            df_s_year, names='Sector', values='Value', 
            title=title_pie,
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
    fig_sector_pie.update_layout(
        margin={"r":5,"t":30,"l":5,"b":5}, 
        height=210,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return [
        dbc.Row(dbc.Col(dcc.Graph(figure=fig_historic_capita), width=12)),
        dbc.Row(dbc.Col(dcc.Graph(figure=fig_sector_pie), width=12)),
    ]

### ADVANCED DATA

# - TOGLE
@callback(
    Output("modal-advanced", "is_open"),
    [Input("open-advanced", "n_clicks"), Input("close-advanced", "n_clicks")],
    [State("modal-advanced", "is_open")],
)
def toggle_advanced_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# -CONTENT
@callback(
    Output("modal-advanced-body", "children"),
    Input("selected-country-store", "data")
)
def update_advanced_modal(country_selected):
    
    # 1. Historical Change in Sectors
    if country_selected:
        df_s_hist = df_sectors[df_sectors['Country'] == country_selected].copy()
        title_hist = f"Historical Sectoral Breakdown: {country_selected}"
    else:
        df_s_hist = df_sectors.groupby(['Year', 'Sector'])['Value'].mean().reset_index()
        title_hist = "Historical Sectoral Breakdown (Global Average)"
    
    if df_s_hist.empty:
        fig_hist_sectors = go.Figure().update_layout(
            title="No data available for this selection",
            height=250, margin={"r":5,"t":30,"l":5,"b":5}
        )
    else:
        df_s_hist = df_s_hist.sort_values('Year')
        fig_hist_sectors = px.area(
            df_s_hist, x="Year", y="Value", color="Sector",
            title=title_hist,
            template='plotly_white',
        )
        fig_hist_sectors.update_layout(margin={"r":5,"t":30,"l":5,"b":5}, height=250)
    
    # 2. Correlation CO2 to each of the sectors
    # We need to merge with totals to get Total CO2 for correlation
    if country_selected:
        df_t = df_totals[df_totals['Country'] == country_selected][['Year', 'Value']].rename(columns={'Value': 'Total_CO2'})
        df_s = df_sectors[df_sectors['Country'] == country_selected]
        df_corr = pd.merge(df_s, df_t, on='Year')
        title_corr = f"Correlation: Total CO2 vs Sectors ({country_selected})"
    else:
        # Global correlation (summed)
        df_t = df_totals.groupby('Year')['Value'].sum().reset_index().rename(columns={'Value': 'Total_CO2'})
        df_s = df_sectors.groupby(['Year', 'Sector'])['Value'].sum().reset_index()
        df_corr = pd.merge(df_s, df_t, on='Year')
        title_corr = "Correlation: Total CO2 vs Sectors (Global)"

    if df_corr.empty:
        fig_sector_corr = go.Figure().update_layout(
            title="No correlation data available",
            height=250, margin={"r":5,"t":35,"l":5,"b":5}
        )
    else:
        fig_sector_corr = px.scatter(
            df_corr, x="Total_CO2", y="Value", color="Sector",
            trendline="ols",
            title=title_corr,
            template='plotly_white'
        )
        fig_sector_corr.update_layout(margin={"r":5,"t":35,"l":5,"b":5}, height=250)
    
    # Placeholder 3 
    fig_p3 = go.Figure().update_layout(
        title="Placeholder 3: Regional Efficiency Trends",
        xaxis={'visible': False}, yaxis={'visible': False},
        annotations=[{'text': 'Coming Soon', 'showarrow': False, 'font': {'size': 14}}],
        margin={"r":5,"t":35,"l":5,"b":5}, height=250
    )

    # Placeholder 4
    fig_p4 = go.Figure().update_layout(
        title="Placeholder 4: Future Emission Projections",
        xaxis={'visible': False}, yaxis={'visible': False},
        annotations=[{'text': 'Coming Soon', 'showarrow': False, 'font': {'size': 14}}],
        margin={"r":5,"t":35,"l":5,"b":5}, height=250
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_hist_sectors, style={'height': '280px'}, config={'responsive': True}), width=6),
            dbc.Col(dcc.Graph(figure=fig_sector_corr, style={'height': '280px'}, config={'responsive': True}), width=6)
        ], className="g-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_p3, style={'height': '280px'}, config={'responsive': True}), width=6),
            dbc.Col(dcc.Graph(figure=fig_p4, style={'height': '280px'}, config={'responsive': True}), width=6)
        ], className="g-1")
    ])