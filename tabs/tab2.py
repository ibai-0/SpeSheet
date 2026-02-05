from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from prepare_data import df_gdp_total, df_gdp_capita, df_life_expectancy, ISO_TO_REGION
from components import controls

def layout():
    return html.Div(className='tab-animacion', children=[
        controls.layout(),
        
        # --- VIEW TOGGLE BUTTONS (GDP vs Life Expectancy) ---
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("GDP", id="btn-tab2-view-gdp", color="primary", size="lg", className="px-5"),
                    dbc.Button("Life Expectancy", id="btn-tab2-view-life", color="outline-primary", size="lg", className="px-5")
                ], className="mb-3 d-flex justify-content-center w-100")
            ], width=12)
        ], className="mb-3"),

        # Hidden store to track which view is active
        dcc.Store(id="tab2-view-mode-store", data="gdp"),
        
        # GDP Stats cards (Top summary cards)
        dbc.Row(id="gdp-stats-container", className="mb-3 g-2"),

        # Controls for GDP view (Radio buttons & Modal Button) - Conditional display
        dbc.Row(id="gdp-controls-row", children=[
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    html.Label("View Mode:", className="fw-bold me-4 mb-0 small"),
                    dbc.RadioItems(
                        id="gdp-view",
                        options=[
                            {"label": "Total GDP", "value": "total"},
                            {"label": "GDP per Capita", "value": "capita"},
                        ],
                        value="total",
                        inline=True,
                        className="small"
                    ),
                ], className="d-flex align-items-center")
            ], className="py-2 px-3"), className="shadow-sm"), width=8),

            dbc.Col(
                dbc.Button(id="advanced-button-text", children="Advanced Prosperity Analysis", 
                           color="primary", className="w-100 shadow-sm h-100", size="sm"),
                width=4
            ),
        ], className="mb-2"),

        # --- GDP VIEW LAYOUT: MAP LEFT, LINES RIGHT ---
        html.Div(id="gdp-layout-container", children=[
            dbc.Row([
                # --- LEFT COLUMN: MAP (Takes 8/12 width) ---
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-map-title-gdp", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-map-description-gdp", className="text-muted small mb-2"),
                        
                        dcc.Graph(id="gdp-map")
                    ]), className="shadow-sm h-100")
                ], width=8),

                # --- RIGHT COLUMN: COUNTRY LINES (Takes 4/12 width) ---
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-lines-title-gdp", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-lines-description-gdp", className="text-muted small mb-2"),
                        
                        dcc.Graph(id="gdp-country-lines")
                    ], className="py-2 px-2"), className="shadow-sm")
                ], width=4)
            ], className="mb-3 g-3")
        ]),

        # --- LIFE EXPECTANCY VIEW LAYOUT: MAP TOP, TWO PLOTS BELOW ---
        html.Div(id="life-layout-container", children=[
            # ROW 1: Full-width Map
            dbc.Row([
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-map-title-life", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-map-description-life", className="text-muted small mb-2"),
                        
                        dcc.Graph(id="gdp-map-life")
                    ]), className="shadow-sm")
                ], width=12)
            ], className="mb-3"),
            
            # ROW 2: Two plots side by side
            dbc.Row([
                # --- LEFT: COUNTRY LINES ---
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-lines-title-life", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-lines-description-life", className="text-muted small mb-2"),
                        
                        dcc.Graph(id="gdp-country-lines-life")
                    ], className="py-2 px-2"), className="shadow-sm")
                ], width=6),
                
                # --- RIGHT: CONTINENTAL PROGRESS ---
                dbc.Col([
                    html.Div(id="tab2-continental-chart-container")
                ], width=6)
            ], className="mb-3 g-3")
        ]),

        # --- MODAL FOR ADVANCED ANALYSIS ---
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="tab2-modal-title")),
                dbc.ModalBody([
                    html.P(id="tab2-modal-intro", className="text-muted mb-4"),
                    html.Div(id="modal-advanced-body-gdp"),
                ]),
                dbc.ModalFooter(dbc.Button("Close", id="close-advanced-gdp", className="ms-auto", size="sm")),
            ],
            id="modal-advanced-gdp",
            size="xl",
            is_open=False,
            scrollable=True,
        ),
    ])

def _get_gdp_df(view):
    """Helper to select the correct dataframe based on user input"""
    return df_gdp_total if view == "total" else df_gdp_capita

# --- CALLBACK 0: TOGGLE VIEW MODE ---
@callback(
    [Output("tab2-view-mode-store", "data"),
     Output("btn-tab2-view-gdp", "color"),
     Output("btn-tab2-view-life", "color")],
    [Input("btn-tab2-view-gdp", "n_clicks"),
     Input("btn-tab2-view-life", "n_clicks")],
    prevent_initial_call=False
)
def toggle_tab2_view_mode(n_gdp, n_life):
    """Toggle between GDP and Life Expectancy views"""
    trigger = ctx.triggered_id if ctx.triggered else None
    
    if trigger == "btn-tab2-view-life":
        return "life", "outline-primary", "primary"
    else:
        return "gdp", "primary", "outline-primary"

# --- CALLBACK 0B: HIDE GDP CONTROLS IN LIFE VIEW ---
@callback(
    Output("gdp-controls-row", "style"),
    Input("tab2-view-mode-store", "data")
)
def toggle_gdp_controls_visibility(view_mode):
    """Hide the GDP/GDP per Capita controls when in Life Expectancy view"""
    if view_mode == "life":
        return {"display": "none"}
    return {}

# --- CALLBACK 0B2: TOGGLE LAYOUT CONTAINERS ---
@callback(
    [Output("gdp-layout-container", "style"),
     Output("life-layout-container", "style")],
    Input("tab2-view-mode-store", "data")
)
def toggle_layout_visibility(view_mode):
    """Show/hide layout containers based on view mode"""
    if view_mode == "life":
        return {"display": "none"}, {}  # Hide GDP, show Life
    else:
        return {}, {"display": "none"}  # Show GDP, hide Life

# --- CALLBACK 0C: UPDATE DYNAMIC TEXT ---
@callback(
    [Output("tab2-map-title-gdp", "children"),
     Output("tab2-map-description-gdp", "children"),
     Output("tab2-lines-title-gdp", "children"),
     Output("tab2-lines-description-gdp", "children"),
     Output("tab2-map-title-life", "children"),
     Output("tab2-map-description-life", "children"),
     Output("tab2-lines-title-life", "children"),
     Output("tab2-lines-description-life", "children"),
     Output("tab2-modal-title", "children"),
     Output("tab2-modal-intro", "children"),
     Output("advanced-button-text", "children")],
    Input("tab2-view-mode-store", "data")
)
def update_tab2_text(view_mode):
    """Update titles and descriptions based on view mode"""
    if view_mode == "life":
        map_title = "Global Life Expectancy Landscape"
        map_desc = [
            "Geospatial distribution of life expectancy. ",
            html.Span("Click on any country", className="fw-bold text-dark bg-light px-1 rounded"),
            " to update the historical analysis below."
        ]
        lines_title = "Life Expectancy Evolution"
        lines_desc = "Comparing the selected nation's life expectancy against the Global Average over time."
        modal_title = "Advanced Life Expectancy Analysis"
        modal_intro = "Deep dive into global health patterns, disparities, and trends for the selected year."
        button_text = "Advanced Health Analysis"
        
        # GDP layout gets empty values (not visible)
        gdp_map_title = ""
        gdp_map_desc = ""
        gdp_lines_title = ""
        gdp_lines_desc = ""
    else:
        gdp_map_title = "Global Economic Landscape"
        gdp_map_desc = [
            "Geospatial distribution of wealth. ",
            html.Span("Click on any country", className="fw-bold text-dark bg-light px-1 rounded"),
            " to update the historical analysis on the right."
        ]
        gdp_lines_title = "Historical Trajectory"
        gdp_lines_desc = "Comparing the selected nation against the Global Average over time (Total & Per Capita)."
        modal_title = "Advanced Economic Analysis"
        modal_intro = "Deep dive into the economic structure, inequality, and stability of nations for the selected year."
        button_text = "Advanced Prosperity Analysis"
        
        # Life layout gets empty values (not visible)
        map_title = ""
        map_desc = ""
        lines_title = ""
        lines_desc = ""
    
    return (gdp_map_title, gdp_map_desc, gdp_lines_title, gdp_lines_desc,
            map_title, map_desc, lines_title, lines_desc,
            modal_title, modal_intro, button_text)

# --- CALLBACK 1: UPDATE STAT CARDS ---
@callback(
    Output("gdp-stats-container", "children"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input('tabs', 'active_tab'),
    Input("tab2-view-mode-store", "data")
)
def update_gdp_cards(selected_year, view, active_tab, view_mode):
    if active_tab != 'tab-2' or selected_year is None:
        return []
    
    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        dff = df_life_expectancy[df_life_expectancy["Year"] == selected_year].dropna(subset=["Life_Expectancy"]).copy()
        
        # Filter out small countries that should have been merged
        # Only keep countries with their main ISO codes after merging
        small_country_isos = {'AND', 'MCO', 'LIE', 'SMR', 'VAT', 'MNE', 'PSE', 'SSD'}
        dff = dff[~dff["ISOcode"].isin(small_country_isos)]
        
        if dff.empty:
            return dbc.Col(dbc.Alert("No data available for this year.", color="warning"), width=12)

        max_row = dff.loc[dff["Life_Expectancy"].idxmax()]
        min_row = dff.loc[dff["Life_Expectancy"].idxmin()]
        mean_val = float(dff["Life_Expectancy"].mean())

        return [
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Global Avg Life Expectancy", className="card-subtitle text-muted small"),
                html.H5(f"{mean_val:.1f} years", className="text-primary mb-0")
            ], className="py-2"), className="border-start border-primary border-4"), width=4),

            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Highest Life Expectancy", className="card-subtitle text-muted small"),
                html.H5(f"{max_row['Country']}", className="text-success mb-0")
            ], className="py-2"), className="border-start border-success border-4"), width=4),

            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Lowest Life Expectancy", className="card-subtitle text-muted small"),
                html.H5(f"{min_row['Country']}", className="text-danger mb-0")
            ], className="py-2"), className="border-start border-danger border-4"), width=4),
        ]
    
    # --- GDP VIEW (ORIGINAL) ---    
    dff = _get_gdp_df(view)
    dff = dff[dff["Year"] == selected_year].dropna(subset=["Value"])
    if dff.empty:
        return dbc.Col(dbc.Alert("No data available for this year.", color="warning"), width=12)

    max_row = dff.loc[dff["Value"].idxmax()]
    mean_val = float(dff["Value"].mean())

    if view == "total":
        global_val = float(dff["Value"].sum())
        left_title = "Global GDP (Sum)"
        left_value = f"{global_val:,.0f} M$"
        right_title = "National Average"
        right_value = f"{mean_val:,.0f} M$"
    else:
        left_title = "Avg GDP per Capita"
        left_value = f"{mean_val:,.0f} $"
        right_title = "Median GDP per Capita"
        right_value = f"{float(dff['Value'].median()):,.0f} $"

    return [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6(left_title, className="card-subtitle text-muted small"),
            html.H5(left_value, className="text-primary mb-0")
        ], className="py-2"), className="border-start border-primary border-4"), width=4),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Maximum GDP", className="card-subtitle text-muted small"),
            html.H5(f"{max_row['Country']}", className="text-danger mb-0")
        ], className="py-2"), className="border-start border-danger border-4"), width=4),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6(right_title, className="card-subtitle text-muted small"),
            html.H5(right_value, className="text-success mb-0")
        ], className="py-2"), className="border-start border-success border-4"), width=4),
    ]

# --- CALLBACK 2: UPDATE MAP ---
@callback(
    [Output("gdp-map", "figure"),
     Output("gdp-map-life", "figure")],
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input('tabs', 'active_tab'),
    Input("tab2-view-mode-store", "data")
)
def update_gdp_map(selected_year, view, active_tab, view_mode):
    if active_tab != 'tab-2' or selected_year is None:
        empty_fig = go.Figure()
        return empty_fig, empty_fig

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        dff = df_life_expectancy[df_life_expectancy["Year"] == selected_year].dropna(subset=["Life_Expectancy"]).copy()
        if dff.empty:
            empty_fig = go.Figure().update_layout(title="No data to show")
            return empty_fig, empty_fig

        fig = px.choropleth(
            dff,
            locations="ISOcode",
            color="Life_Expectancy",
            hover_name="Country",
            hover_data={"Life_Expectancy": ":.1f", "ISOcode": False},
            color_continuous_scale="RdYlGn",
            height=400
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Age", thickness=15, len=0.6),
            geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
            annotations=[dict(
                x=0.5, y=-0.1, xref='paper', yref='paper',
                text="Interactive: Select a country to see details >",
                showarrow=False, font=dict(size=12, color="gray")
            )]
        )
        return fig, fig

    # --- GDP VIEW (ORIGINAL) ---
    dff = _get_gdp_df(view)
    dff = dff[dff["Year"] == selected_year].dropna(subset=["Value"]).copy()
    dff = dff[dff["Value"] > 0]

    if dff.empty:
        empty_fig = go.Figure().update_layout(title="No data to show")
        return empty_fig, empty_fig

    # Log scale is used to visualize differences between massive economies (USA, China) and smaller ones.
    dff["ColorValue"] = np.log10(dff["Value"])

    fig = px.choropleth(
        dff,
        locations="ISOcode",
        color="ColorValue",
        hover_name="Country",
        hover_data={"Value": ":,.2f", "ColorValue": False},
        color_continuous_scale="Viridis",
        height=550
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="log10(GDP)", thickness=15, len=0.6),
        geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
        annotations=[dict(
            x=0.5, y=-0.1, xref='paper', yref='paper',
            text="Interactive: Select a country to see details >",
            showarrow=False, font=dict(size=12, color="gray")
        )]
    )
    return fig, fig

# --- CALLBACK 3: UPDATE SIDE LINES (HISTORY) ---
@callback(
    [Output("gdp-country-lines", "figure"),
     Output("gdp-country-lines-life", "figure")],
    [Input("gdp-map", "clickData"),
     Input("gdp-map-life", "clickData")],
    Input("year-slider", "value"),
    Input('tabs', 'active_tab'),
    Input("tab2-view-mode-store", "data")
)
def update_country_lines(clickData_gdp, clickData_life, selected_year, active_tab, view_mode):
    if active_tab != 'tab-2' or selected_year is None:
        empty_fig = go.Figure()
        return empty_fig, empty_fig

    # Choose the appropriate clickData based on view mode
    clickData = clickData_life if view_mode == "life" else clickData_gdp
    
    iso = None
    if clickData and clickData.get("points"):
        iso = clickData["points"][0].get("location")

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        # Fallback: If no country is selected, default to the one with max life expectancy
        dff_y = df_life_expectancy[df_life_expectancy["Year"] == selected_year].dropna(subset=["Life_Expectancy"])
        if iso is None and not dff_y.empty:
            iso = dff_y.loc[dff_y["Life_Expectancy"].idxmax(), "ISOcode"]

        if iso is None:
            empty_fig = go.Figure().update_layout(title="Click on a country")
            return empty_fig, empty_fig

        # Fetch data for the selected country
        c_life = df_life_expectancy[df_life_expectancy["ISOcode"] == iso].dropna(subset=["Life_Expectancy"]).copy()
        
        if c_life.empty:
            empty_fig = go.Figure().update_layout(title="No data for selected country")
            return empty_fig, empty_fig
        
        name = c_life["Country"].iloc[0]

        # Calculate Global Average for comparison
        avg_life = df_life_expectancy.dropna(subset=["Life_Expectancy"]).groupby("Year")["Life_Expectancy"].mean().reset_index()

        # Create single line chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=c_life["Year"], 
            y=c_life["Life_Expectancy"], 
            mode="lines", 
            name=f"{name}",
            line=dict(width=3, color='#2ecc71')
        ))
        
        fig.add_trace(go.Scatter(
            x=avg_life["Year"], 
            y=avg_life["Life_Expectancy"], 
            mode="lines",
            name="Global Average", 
            line=dict(color="gray", dash="dash", width=2)
        ))

        # Add a vertical line to indicate the selected year from the slider
        fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")
        
        # Update hover template for cleaner display
        fig.update_traces(
            hovertemplate="%{fullData.name}<br>Year: %{x}<br>Life Exp: %{y:.1f} years<extra></extra>"
        )

        fig.update_layout(
            height=450,
            template="plotly_white",
            showlegend=True,
            legend=dict(orientation="h", y=-0.3, font=dict(size=9)),
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            yaxis_title="Life Expectancy (years)",
            xaxis_title="Year"
        )
        return fig, fig

    # --- GDP VIEW (ORIGINAL) ---
    # Fallback: If no country is selected, default to the one with max GDP
    dff_y = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    if iso is None and not dff_y.empty:
        iso = dff_y.loc[dff_y["Value"].idxmax(), "ISOcode"]

    if iso is None:
        empty_fig = go.Figure().update_layout(title="Click on a country")
        return empty_fig, empty_fig

    # Fetch data for the selected country
    c_total = df_gdp_total[df_gdp_total["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    c_cap = df_gdp_capita[df_gdp_capita["ISOcode"] == iso].dropna(subset=["Value"]).copy()

    name = c_total["Country"].iloc[0] if not c_total.empty else c_cap["Country"].iloc[0]

    # Calculate Global Averages for comparison
    avg_total = df_gdp_total.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_cap = df_gdp_capita.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()

    # Create Subplots: 2 vertical charts
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=(f"Total GDP ({name})", f"GDP per Capita ({name})"),
                        vertical_spacing=0.15)

    # 1. Total GDP Line
    fig.add_trace(go.Scatter(x=c_total["Year"], y=c_total["Value"], mode="lines", name=f"{name} (Total)", 
                             line=dict(width=3), hovertemplate="Year: %{x}<br>GDP: $%{y:,.0f}M<extra></extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=avg_total["Year"], y=avg_total["Value"], mode="lines",
                             name="Global Avg", line=dict(color="gray", dash="dash"),
                             hovertemplate="Year: %{x}<br>Avg: $%{y:,.0f}M<extra></extra>"),
                  row=1, col=1)

    # 2. Per Capita Line
    fig.add_trace(go.Scatter(x=c_cap["Year"], y=c_cap["Value"], mode="lines", name=f"{name} (Per Capita)", 
                             line=dict(width=3), showlegend=True,
                             hovertemplate="Year: %{x}<br>GDP pc: $%{y:,.0f}<extra></extra>"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=avg_cap["Year"], y=avg_cap["Value"], mode="lines",
                             name="Global Avg", line=dict(color="gray", dash="dash"), showlegend=False,
                             hovertemplate="Year: %{x}<br>Avg: $%{y:,.0f}<extra></extra>"),
                  row=2, col=1)

    # Add a vertical line to indicate the selected year from the slider
    fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")

    fig.update_layout(
        height=550,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified"
    )
    return fig, fig

# --- CALLBACK 3B: CONTINENTAL PROGRESS CHART (LIFE EXPECTANCY VIEW ONLY) ---
@callback(
    Output("tab2-continental-chart-container", "children"),
    Input("year-slider", "value"),
    Input('tabs', 'active_tab'),
    Input("tab2-view-mode-store", "data")
)
def update_continental_progress(selected_year, active_tab, view_mode):
    if active_tab != 'tab-2' or view_mode != "life" or selected_year is None:
        return None
    
    # Map countries to continents
    df_with_continent = df_life_expectancy.copy()
    df_with_continent["Continent"] = df_with_continent["ISOcode"].map(ISO_TO_REGION).fillna("Other")
    df_with_continent = df_with_continent[df_with_continent["Continent"] != "Other"]
    
    # Calculate average life expectancy by continent and year (all years)
    continent_avg = df_with_continent.groupby(["Year", "Continent"], as_index=False)["Life_Expectancy"].mean()
    
    # Color mapping - each region gets unique color
    color_map = {
        'Europe & Central Asia': '#3498db',       # Blue
        'East Asia & Pacific': '#e74c3c',         # Red
        'South Asia': '#9b59b6',                  # Purple
        'North America': '#2ecc71',               # Green
        'Latin America & Caribbean': '#1abc9c',   # Teal
        'Middle East & North Africa': '#f39c12',  # Orange
        'Sub-Saharan Africa': '#f1c40f',          # Yellow
    }
    
    # Create line chart
    fig = px.line(
        continent_avg,
        x="Year",
        y="Life_Expectancy",
        color="Continent",
        template="plotly_white",
        markers=True,
        color_discrete_map=color_map
    )
    
    # Add vertical line for selected year
    fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")
    
    # Update hover template to show cleaner info
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Life Exp: %{y:.1f} years<extra></extra>"
    )
    
    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        yaxis_title="Life Expectancy (years)",
        xaxis_title="Year",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.4,
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        )
    )
    
    return dbc.Card(dbc.CardBody([
        html.H5("Continental Progress", className="text-primary fw-bold mb-1"),
        html.P("Average life expectancy evolution by continent over time.", 
               className="text-muted small mb-2"),
        dcc.Graph(figure=fig)
    ], className="py-2 px-2"), className="shadow-sm")

# --- CALLBACK 4: MODAL OPEN/CLOSE ---
@callback(
    Output("modal-advanced-gdp", "is_open"),
    [Input("advanced-button-text", "n_clicks"), Input("close-advanced-gdp", "n_clicks")],
    [State("modal-advanced-gdp", "is_open")]
)
def toggle_modal_gdp(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# --- CALLBACK 5: UPDATE ADVANCED GRAPHS INSIDE MODAL ---
@callback(
    Output("modal-advanced-body-gdp", "children"),
    Input("year-slider", "value"),
    Input('tabs', 'active_tab'),
    Input("tab2-view-mode-store", "data")
)
def update_advanced_modal_gdp(selected_year, active_tab, view_mode):
    if active_tab != 'tab-2' or selected_year is None:
        return None

    # --- LIFE EXPECTANCY ADVANCED ANALYSIS ---
    if view_mode == "life":
        return create_life_expectancy_advanced_analysis(selected_year)
    
    # --- GDP ADVANCED ANALYSIS (ORIGINAL) ---
    return create_gdp_advanced_analysis(selected_year)


def create_gdp_advanced_analysis(selected_year):
    """Create GDP advanced analysis charts"""

    # 1. TREEMAP: Top 15 Total GDP
    d1 = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    top_total = d1.nlargest(15, "Value")
    
    fig1 = px.treemap(
        top_total,
        path=['Country'],
        values='Value',
        color='Value',
        color_continuous_scale='Viridis',
        template="plotly_white"
    )

    # 2. LOLLIPOP CHART: Top 10 GDP per Capita
    d2 = df_gdp_capita[df_gdp_capita["Year"] == selected_year].dropna(subset=["Value"])
    top_cap = d2.nlargest(10, "Value").sort_values("Value")
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=top_cap["Value"],
        y=top_cap["Country"],
        mode='markers',
        marker=dict(size=12, color='mediumturquoise'),
        name="GDP pc"
    ))
    
    shapes = []
    for i, row in top_cap.iterrows():
        shapes.append(dict(
            type="line",
            xref="x", yref="y",
            x0=0, y0=row["Country"],
            x1=row["Value"], y1=row["Country"],
            line=dict(color="lightgray", width=2)
        ))
        
    fig2.update_layout(
        shapes=shapes,
        xaxis=dict(title="GDP per Capita ($)"),
        yaxis=dict(title=""),
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False
    )

    # 3. SCATTER PLOT: Risk vs Return
    hist = df_gdp_total[df_gdp_total["Year"] <= selected_year].dropna(subset=["Value"]).copy()
    hist = hist[hist["Value"] > 0].sort_values(["ISOcode", "Year"])
    hist["pct_yoy"] = hist.groupby("ISOcode")["Value"].pct_change() * 100
    
    name_map = hist.groupby("ISOcode")["Country"].first().to_dict()

    risk_return = hist.groupby("ISOcode")["pct_yoy"].agg(['mean', 'std']).dropna()
    risk_return = risk_return.rename(columns={'mean': 'Avg_Growth', 'std': 'Volatility'})
    risk_return["Country"] = risk_return.index.map(name_map)
    risk_return = risk_return[risk_return['Avg_Growth'] < 50] 

    fig3 = px.scatter(
        risk_return,
        x="Avg_Growth",
        y="Volatility",
        hover_name="Country",
        size="Volatility",
        labels={"Avg_Growth": "Avg Growth (%)", "Volatility": "Volatility (Std Dev)"},
        template="plotly_white"
    )
    fig3.add_hline(y=risk_return['Volatility'].median(), line_dash="dash", line_color="gray")
    fig3.add_vline(x=0, line_color="gray")

    # 4. DUMBBELL PLOT: Growth Amplitude
    std_dev = hist.groupby("ISOcode")["pct_yoy"].std()
    top_volatile_iso = std_dev.nlargest(10).index
    
    df_vol = hist[hist["ISOcode"].isin(top_volatile_iso)]
    
    stats = df_vol.groupby("Country")["pct_yoy"].agg(['min', 'max']).reset_index()
    stats['range'] = stats['max'] - stats['min']
    stats = stats.sort_values('range', ascending=True)

    fig4 = go.Figure()

    for i, row in stats.iterrows():
        fig4.add_trace(go.Scatter(
            x=[row['min'], row['max']],
            y=[row['Country'], row['Country']],
            mode='lines',
            line=dict(color='lightgray', width=3),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig4.add_trace(go.Scatter(
        x=stats['min'], y=stats['Country'], mode='markers', name='Min Growth',
        marker=dict(color='#e74c3c', size=10), hovertemplate='%{y}: Min %{x:.1f}%<extra></extra>'
    ))

    fig4.add_trace(go.Scatter(
        x=stats['max'], y=stats['Country'], mode='markers', name='Max Growth',
        marker=dict(color='#2ecc71', size=10), hovertemplate='%{y}: Max %{x:.1f}%<extra></extra>'
    ))

    fig4.update_layout(
        xaxis_title="Annual Growth (%)",
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10), 
        legend=dict(orientation="h", y=-0.2),
        hovermode="closest"
    )

    for f in [fig1, fig2, fig3, fig4]:
        f.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)

    # --- ADVANCED ANALYSIS MODAL LAYOUT ---
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("Global Economic Weight (Treemap)", className="text-primary fw-bold"),
                html.P("Size represents total GDP share. Who dominates the global economy?", className="text-muted small"),
                dcc.Graph(figure=fig1)
            ], width=6),
            dbc.Col([
                html.H6("Top Wealth per Capita (Lollipop)", className="text-primary fw-bold"),
                html.P("Ranking of the richest nations per person. Note the gap between top economies.", className="text-muted small"),
                dcc.Graph(figure=fig2)
            ], width=6),
        ], className="g-3 mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.H6("Risk vs Return (Stability)", className="text-primary fw-bold"),
                html.P("Horizontal axis: Avg Growth. Vertical axis: Instability. High bubbles = Unstable growth.", className="text-muted small"),
                dcc.Graph(figure=fig3)
            ], width=6),
            dbc.Col([
                html.H6("Extreme Volatility Ranges", className="text-primary fw-bold"),
                html.P("For the most unstable countries: The distance between their best (green) and worst (red) year.", className="text-muted small"),
                dcc.Graph(figure=fig4)
            ], width=6),
        ], className="g-3"),
    ])


def create_life_expectancy_advanced_analysis(selected_year):
    """Create Life Expectancy advanced analysis charts"""
    
    # 1. TREEMAP: Top 15 Life Expectancy
    d1 = df_life_expectancy[df_life_expectancy["Year"] == selected_year].dropna(subset=["Life_Expectancy"])
    top_life = d1.nlargest(15, "Life_Expectancy")
    
    fig1 = px.treemap(
        top_life,
        path=['Country'],
        values='Life_Expectancy',
        color='Life_Expectancy',
        color_continuous_scale='RdYlGn',
        template="plotly_white"
    )

    # 2. LOLLIPOP CHART: Bottom 10 Life Expectancy (lowest)
    bottom_life = d1.nsmallest(10, "Life_Expectancy").sort_values("Life_Expectancy")
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=bottom_life["Life_Expectancy"],
        y=bottom_life["Country"],
        mode='markers',
        marker=dict(size=12, color='#e74c3c'),
        name="Life Exp"
    ))
    
    shapes = []
    for i, row in bottom_life.iterrows():
        shapes.append(dict(
            type="line",
            xref="x", yref="y",
            x0=0, y0=row["Country"],
            x1=row["Life_Expectancy"], y1=row["Country"],
            line=dict(color="lightgray", width=2)
        ))
        
    fig2.update_layout(
        shapes=shapes,
        xaxis=dict(title="Life Expectancy (years)"),
        yaxis=dict(title=""),
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False
    )

    # 3. BOX PLOT: Regional Distribution
    # Need to map countries to regions
    df_with_region = d1.copy()
    df_with_region["Region"] = df_with_region["ISOcode"].map(ISO_TO_REGION).fillna("Other")
    df_with_region = df_with_region[df_with_region["Region"] != "Other"]
    
    fig3 = px.box(
        df_with_region,
        x="Region",
        y="Life_Expectancy",
        color="Region",
        template="plotly_white",
        points="all"
    )
    fig3.update_layout(showlegend=False, xaxis_tickangle=-45)

    # 4. HISTOGRAM: Life Expectancy Distribution
    fig4 = px.histogram(
        d1,
        x="Life_Expectancy",
        nbins=30,
        template="plotly_white",
        color_discrete_sequence=['#3498db']
    )
    fig4.update_layout(
        xaxis_title="Life Expectancy (years)",
        yaxis_title="Number of Countries",
        showlegend=False
    )
    
    # Add mean line
    mean_life = d1["Life_Expectancy"].mean()
    fig4.add_vline(x=mean_life, line_dash="dash", line_color="red", 
                   annotation_text=f"Global Mean: {mean_life:.1f}",
                   annotation_position="top right")

    for f in [fig1, fig2, fig3, fig4]:
        f.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)

    # --- LIFE EXPECTANCY ADVANCED ANALYSIS MODAL LAYOUT ---
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("Top Life Expectancy Countries (Treemap)", className="text-primary fw-bold"),
                html.P("Size represents life expectancy value. Which countries have the healthiest populations?", className="text-muted small"),
                dcc.Graph(figure=fig1)
            ], width=6),
            dbc.Col([
                html.H6("Countries with Lowest Life Expectancy (Lollipop)", className="text-primary fw-bold"),
                html.P("Ranking of countries facing the greatest health challenges. Note the significant gaps.", className="text-muted small"),
                dcc.Graph(figure=fig2)
            ], width=6),
        ], className="g-3 mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.H6("Regional Life Expectancy Distribution", className="text-primary fw-bold"),
                html.P("How does life expectancy vary within and across regions? Each point represents a country.", className="text-muted small"),
                dcc.Graph(figure=fig3)
            ], width=6),
            dbc.Col([
                html.H6("Global Life Expectancy Distribution", className="text-primary fw-bold"),
                html.P("Histogram showing how many countries fall into each life expectancy range. Are we converging?", className="text-muted small"),
                dcc.Graph(figure=fig4)
            ], width=6),
        ], className="g-3"),
    ])