from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from prepare_data import df_totals, df_capita, df_sectors
from components import controls

def layout():
    """
    Constructs the layout for Tab 1 (Emissions Map).
    Includes the common control bar, status cards, and the main geospatial map 
    with a side panel for continental analysis.
    """
    return html.Div(className='tab-animacion', children=[
        # --- TOP CONTROL BAR (Shared across tabs) ---
        controls.layout(),
        
        # --- STATUS INDICATORS (Summary statistics for selected year) ---
        dbc.Row(id='stats-container', className="mb-3 g-2"),
        
        # --- MAIN VISUALIZATION ROW ---
        dbc.Row([
            # LEFT COLUMN: Global Choropleth Map
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5("Global Carbon Landscape", className="text-primary fw-bold mb-1"),
                    html.P([
                        "How is the global carbon footprint distributed? This map visualizes total CO₂ emissions (Mt) by country. Darker shades reveal the world's largest absolute emitters. ",
                        html.Span("Click on any nation", className="fw-bold text-dark bg-light px-1 rounded"),
                        " to deep-dive into its sectoral fingerprint."
                    ], className="text-muted small mb-2"),
                    
                    # The primary interactive map
                    dcc.Graph(id='map-graph'),
                    
                    # Global status button triggers analysis when no country is clicked
                    dbc.Button("Global Analysis", id="reset-global-btn", n_clicks=0, color="primary", className="w-100 mt-2 shadow-sm", size="sm"),
                ]), className="shadow-sm h-100")
            ], width=8),
            
            # RIGHT COLUMN: Contextual Analysis (Treemap)
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H6("Regional Carbon Landscape", className="text-primary fw-bold mb-1"),
                    html.P("Who are the primary contributors? This hierarchical view breaks down global emissions.", className="text-muted small mb-1"),
                    dcc.Graph(id='treemap-graph', style={'height': '420px'})
                ]), className="shadow-sm h-100")
            ], width=4)
        ], className="g-3 mb-3"),
        
        # --- INTERACTIVE MODAL (Detailed Analysis Popup) ---
        # Triggered by clicking a country on the map or the "Analyze Global Status" button
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Detailed Country Analysis"), close_button=True),
            dbc.ModalBody([
                html.Div(id="modal-advanced-body"),
                html.Hr(className="my-2"),
                dbc.Button("Close analysis", id="close-advanced", color="secondary", className="float-end btn-sm mb-2"),
            ]),
        ], id="modal-advanced", size="xl", is_open=False),
        
        # --- STATE MANAGEMENT ---
        # Store for maintaining the selected country identification (Name or ISO)
        dcc.Store(id='selected-country-store', data=None),
    ])


# -----------------------------------------------------------------------------
# 1. CALLBACK: GLOBAL MAP UPDATE
# -----------------------------------------------------------------------------
@callback(
    Output('map-graph', 'figure'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value')
)
def update_map(tab, selected_year):
    """
    Updates the choropleth map based on the year slider.
    Only executes if Tab 1 is active.
    """
    if tab != 'tab-1' or selected_year is None:
        return go.Figure()
    
    # Filter data for the specific temporal snapshot
    dff = df_totals[df_totals['Year'] == selected_year]
    
    # Generate the map using Viridis scale (standard for visibility)
    fig_map = px.choropleth(
        dff, locations="ISOcode", color="Value", hover_name="Country",
        color_continuous_scale="Viridis", height=450 # Adjusted to match Tab 2
    )
    fig_map.update_layout(
        margin={"r":0,"t":25,"l":0,"b":0}, 
        transition_duration=100,
        coloraxis_colorbar=dict(title="CO2 (Mt)", thickness=15, len=0.8)
    )
    return fig_map

# -----------------------------------------------------------------------------
# 2. CALLBACK: COUNTRY SELECTION MANAGEMENT
# -----------------------------------------------------------------------------
@callback(
    Output('selected-country-store', 'data'),
    Input('map-graph', 'clickData'),
    Input('reset-global-btn', 'n_clicks'),
    prevent_initial_call=False
)
def update_country_store(clickData, n_clicks):
    """
    Captures country selection from map clicks or resets selection to 'Global'.
    Treemap interaction is handled locally by the component for zooming.
    """
    # Check if the trigger was the reset button
    if ctx.triggered_id == 'reset-global-btn':
        return None
    
    # Retrieve country name from hovertext metadata in clickData
    if clickData and 'points' in clickData:
        return clickData['points'][0]['hovertext']
    return None

# -----------------------------------------------------------------------------
# 3. CALLBACK: MODAL TOGGLE LOGIC
# -----------------------------------------------------------------------------
@callback(
    Output("modal-advanced", "is_open"),
    [Input("selected-country-store", "data"), 
     Input("reset-global-btn", "n_clicks"),
     Input("close-advanced", "n_clicks")],
    [State("modal-advanced", "is_open")],
)
def toggle_advanced_modal(country_selected, n_global, n_close, is_open):
    """
    Logic for opening and closing the detailed analysis modal based on 
    user interaction (clicks or explicit close button).
    """
    triggered_id = ctx.triggered_id
    
    # If resetting to global view, open modal for global summary
    if triggered_id == "reset-global-btn":
        return True
    
    # If a country is selected via map, open modal for specific analysis
    if triggered_id == "selected-country-store":
        if country_selected:
            return True
        return is_open
    
    # Explicit close action
    if triggered_id == "close-advanced":
        return False
        
    return is_open

@callback(
    Output('treemap-graph', 'figure'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value')
)
def update_treemap(tab, selected_year):
    """
    Generates the regional distribution treemap for the current year.
    Uses uirevision to preserve zoom/path state across year changes.
    """
    if tab != 'tab-1' or selected_year is None:
        return go.Figure()

    dff_now = df_totals[df_totals['Year'] == selected_year].copy()
    
    fig_tree = px.treemap(
        dff_now, path=[px.Constant("World"), 'Continent', 'Country'],
        values='Value', color='Continent',
        hover_data={'Value': ':,.2f Mt'},
        height=420
    )
    fig_tree.update_layout(
        margin={"r":5,"t":5,"l":5,"b":5},
        template='plotly_white',
        uirevision='constant' # Maintains zoom/path state
    )
    return fig_tree

# -----------------------------------------------------------------------------
# 5. CALLBACK: ADVANCED MODAL CONTENT (DEEP ANALYSIS)
# -----------------------------------------------------------------------------
@callback(
    Output("modal-advanced-body", "children"),
    Input("selected-country-store", "data"),
    Input('year-slider', 'value')
)
def update_advanced_modal(country_selected, selected_year):
    """
    Renders complex analytical content for the modal:
    Historical per capita trends, sectoral breakdowns, and radar profile benchmarking.
    """
    # Baseline data preparation
    dff_now = df_totals[df_totals['Year'] == selected_year].copy()
    df_1970 = df_totals[df_totals['Year'] == 1970][['Country', 'Value']].rename(columns={'Value': 'Value_1970'})
    
    # Cumulative calculation (Historical Debt)
    df_cumulative_sum = df_totals[df_totals['Year'] <= selected_year].groupby('Country')['Value'].sum().reset_index()
    df_cumulative_sum.columns = ['Country', 'Cumulative_Debt']

    if country_selected:
        # --- SPECIFIC COUNTRY VIEW ---
        # Historical Intensity (per person)
        df_capita_sel = df_capita[df_capita['Country'] == country_selected]
        fig_capita = px.line(df_capita_sel, x='Year', y='Value', title=f"CO2 per Capita: {country_selected}")
        
        # Sectoral distribution
        df_sectors_sel = df_sectors[(df_sectors['Country'] == country_selected) & (df_sectors['Year'] == selected_year)]
        fig_pie = px.pie(df_sectors_sel, names='Sector', values='Value', title=f"Sectors: {country_selected}", hole=0.4)
        
        # Structural evolution over time
        df_s_hist = df_sectors[df_sectors['Country'] == country_selected].sort_values('Year')
        fig_area = px.area(df_s_hist, x="Year", y="Value", color="Sector", title="Sector Evolution")
        
        radar_title = f"Top 5 vs {country_selected} (Normalized)"
        target_radar = country_selected
    else:
        # --- GLOBAL AGGREGATIONS VIEW ---
        # World Avg per Capita
        df_capita_world = df_capita.groupby('Year')['Value'].mean().reset_index()
        fig_capita = px.line(df_capita_world, x='Year', y='Value', title="World Average CO2 per Capita")
        
        # Global Sector Sum
        df_sectors_world = df_sectors[df_sectors['Year'] == selected_year].groupby('Sector')['Value'].sum().reset_index()
        fig_pie = px.pie(df_sectors_world, names='Sector', values='Value', title="Global Sectoral Impact", hole=0.4)
        
        # World Sector Evolution
        df_s_hist_world = df_sectors.groupby(['Year', 'Sector'])['Value'].sum().reset_index()
        fig_area = px.area(df_s_hist_world, x="Year", y="Value", color="Sector", title="Global Sector Evolution")
        
        radar_title = "Global Top 5 Emitters Profile"
        target_radar = dff_now.nlargest(1, 'Value')['Country'].iloc[0]

    # Common layout styles
    for f in [fig_capita, fig_pie, fig_area]:
        f.update_layout(margin={"r":5,"t":35,"l":5,"b":5}, height=250, template='plotly_white')
    
    # Synchronized Year Indicators (Moving Lines)
    for f in [fig_capita, fig_area]:
        f.add_vline(x=selected_year, line_dash="dash", line_color="red")

    # --- RADAR LOGIC (Benchmarking) ---
    # Normalizes diverse metrics (Absolute Emissions, Growth Speed, Cumulative Debt)
    # to allow visual comparison of different country profiles.
    top5_list = dff_now.nlargest(5, 'Value')['Country'].tolist()
    compare_list = list(set(top5_list + ([target_radar.strip()] if target_radar else [])))
    
    # Consolidate metrics for the radar axes
    df_metrics = pd.merge(dff_now[dff_now['Country'].isin(compare_list)], df_1970, on='Country', how='left')
    df_metrics = pd.merge(df_metrics, df_cumulative_sum, on='Country', how='left')
    
    # Calculate Growth Speed (current / baseline)
    df_metrics['Growth_Multiplier'] = df_metrics.apply(
        lambda x: x['Value'] / x['Value_1970'] if pd.notnull(x['Value_1970']) and x['Value_1970'] > 0 else 1, axis=1
    )
    
    # Rename metrics for human-readable radar categories
    df_metrics = df_metrics.rename(columns={
        'Value': 'Current Scale',
        'Growth_Multiplier': 'Growth Speed',
        'Cumulative_Debt': 'Historical Debt'
    })
    
    # Normalize by max value in the selection set to scale metrics 0-1
    df_spider = df_metrics.copy()
    for col in ['Current Scale', 'Growth Speed', 'Historical Debt']:
        max_val = df_spider[col].max()
        if max_val > 0:
            df_spider[col] = df_spider[col] / max_val

    # Melt to long format for Plotly Radar implementation
    df_radar_long = df_spider.melt(id_vars='Country', 
                                   value_vars=['Current Scale', 'Growth Speed', 'Historical Debt'],
                                   var_name='Metric', value_name='Score')

    fig_radar = px.line_polar(
        df_radar_long, r='Score', theta='Metric', color='Country',
        line_close=True, title=radar_title, template='plotly_white'
    )
    
    # Highlighting selected country in the radar (Thicker line for better focus)
    for trace in fig_radar.data:
        if country_selected and trace.name == country_selected:
            trace.line.width = 4
            trace.marker.size = 10
        else:
            trace.line.width = 2
            trace.line.dash = 'dot'

    fig_radar.update_layout(margin={"r":5,"t":60,"l":5,"b":5}, height=250, 
                            polar=dict(radialaxis=dict(visible=True, range=[0, 1])))

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("Sectoral Fingerprint", className="text-primary fw-bold mb-1"),
                html.P("Identifying the primary mechanical drivers of emissions. Which industry holds the largest industrial legacy?", className="text-muted small mb-2"),
                dcc.Graph(figure=fig_pie)
            ], width=6),
            dbc.Col([
                html.H6("Individual Footprint (Efficiency Frontier)", className="text-primary fw-bold mb-1"),
                html.P("Measuring the carbon cost per person. A high value here suggests a lifestyle of extreme environmental intensity.", className="text-muted small mb-2"),
                dcc.Graph(figure=fig_capita)
            ], width=6)
        ], className="g-3 mb-4"),
        dbc.Row([
            dbc.Col([
                html.H6("Structural Transitions", className="text-primary fw-bold mb-1"),
                html.P("Decades of shifting industrial bases. Observe how Power Industry, Transport, and Buildings evolve over time as nations industrialize or move toward cleaner energy grids.", className="text-muted small mb-2"),
                dcc.Graph(figure=fig_area)
            ], width=6),
            dbc.Col([
                html.H6("Environmental Responsibility Profile", className="text-primary fw-bold mb-1"),
                html.P([
                    "Benchmarking systemic impact across three axes: ",
                    html.B("Scale"), " (Mt intensity), ",
                    html.B("Growth"), " (expansion speed since 1970), and ",
                    html.B("Debt"), " (total historical footprint)."
                ], className="text-muted small mb-2"),
                dcc.Graph(figure=fig_radar)
            ], width=6)
        ], className="g-3")
    ])