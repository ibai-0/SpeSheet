from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from prepare_data import (
    TAB3_LIFE_REGION_COLOR_MAP,
    tab3_get_gdp_bubble_year_df,
    tab3_get_life_bubble_year_df,
    tab3_get_gdp_country_trajectory_df,
    tab3_get_life_country_trajectory_df,
    tab3_get_decoupling_delta,
    tab3_get_life_progress_delta,
)
from components import controls

# ==================== UTILITY FUNCTIONS ====================

def add_selection_ring(fig, df, selected_iso, x_col, y_col):
    """Add a black ring around the selected country"""
    if selected_iso:
        selected = df[df["ISOcode"] == selected_iso]
        if not selected.empty:
            fig.add_trace(go.Scatter(
                x=selected[x_col],
                y=selected[y_col],
                mode='markers',
                marker=dict(size=20, color='rgba(0,0,0,0)', symbol='circle', 
                           line=dict(width=3, color='black')),
                showlegend=False,
                hoverinfo='skip'
            ))
    return fig

def create_baseline_figure(year, message):
    """Create placeholder figure for baseline year"""
    return go.Figure().update_layout(
        template="plotly_white",
        xaxis={"visible": False}, 
        yaxis={"visible": False},
        annotations=[{
            "text": f"<b>Baseline Year: {year}</b><br>{message}", 
            "showarrow": False, 
            "font": {"size": 16, "color": "gray"}
        }]
)

def add_quadrant_zones(fig, zones):
    """Add colored quadrant zones with labels to figure"""
    for zone in zones:
        fig.add_shape(
            type="rect", 
            x0=zone["x0"], x1=zone["x1"], 
            y0=zone["y0"], y1=zone["y1"], 
            fillcolor=zone["color"], 
            opacity=0.1, 
            layer="below", 
            line_width=0
        )
        if "label" in zone:
            fig.add_annotation(
                x=zone["label_x"], 
                y=zone["label_y"], 
                text=f"<b>{zone['label']}</b>", 
                showarrow=False, 
                font=dict(color=zone["color"], size=zone.get("label_size", 12))
            )
    return fig

def create_ranking_html(top_df, bottom_df, top_title, bottom_title, metrics_formatter):
    """Create HTML ranking section with top and bottom performers
    
    Args:
        top_df: DataFrame with top performers
        bottom_df: DataFrame with bottom performers
        top_title: Title for top section
        bottom_title: Title for bottom section
        metrics_formatter: Function that takes a row and returns the metrics HTML
    """
    def create_cards(df):
        cards = []
        for i, (idx, row) in enumerate(df.iterrows()):
            cards.append(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Span(f"{i+1}. ", className="fw-bold text-muted me-2"),
                        html.Span(row['Country'], className="fw-bold"),
                    ]),
                    html.Small(metrics_formatter(row), className="text-muted")
                ], className="py-2 px-3")
            ], className="mb-2"))
        return cards
    
    return dbc.Row([
        dbc.Col([
            html.H6(top_title, className="text-success fw-bold mb-3"),
            html.Div(create_cards(top_df))
        ], width=6),
        dbc.Col([
            html.H6(bottom_title, className="text-danger fw-bold mb-3"),
            html.Div(create_cards(bottom_df))
        ], width=6)
    ])

# ==================== LAYOUT ====================

def layout():
    return html.Div(className='tab-animacion', children=[
        
        # --- CONTROL BAR (Year Slider & Region Filter) ---
        controls.layout(),

        # --- VIEW TOGGLE BUTTONS ---
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("GDP", id="btn-view-gdp", color="primary", size="lg", className="px-5"),
                    dbc.Button("Life Expectancy", id="btn-view-life", color="outline-primary", size="lg", className="px-5")
                ], className="mb-3 d-flex justify-content-center w-100")
            ], width=12)
        ], className="mb-3"),

        # Hidden store to track which view is active
        dcc.Store(id="view-mode-store", data="gdp"),

        dbc.Row([
            # -------------------------------------------------------------
            # LEFT COLUMN: MAIN BUBBLE CHART 
            # -------------------------------------------------------------
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    # Title and Context for the user
                    html.H5(id="bubble-chart-title", className="text-primary fw-bold mb-1"),
                    html.P(id="bubble-chart-description", className="text-muted small mb-3"),
                    
                    # The Main Graph
                    dcc.Graph(id='corr-bubble-graph', style={'height': '600px'}) 
                ]), className="shadow-sm h-100")
            ], width=8),
            
            # -------------------------------------------------------------
            # RIGHT COLUMN: SIDE ANALYSIS & CONTROLS 
            # -------------------------------------------------------------
            dbc.Col([
                # 1. STATISTICS CARD
                dbc.Card(dbc.CardBody([
                    html.H6("Snapshot Statistics", className="card-subtitle text-muted fw-bold small mb-2"),
                    html.P(id="stats-description", className="small text-secondary mb-2"),
                    
                    # Dynamic Values
                    html.H2(id="corr-value-display", className="text-center my-2 fw-bold text-dark"),
                    html.P(id="corr-explanation-display", className="text-center text-muted small mb-0")
                ]), className="shadow-sm mb-3"),

                # 2. TRAJECTORY GRAPH (KUZNETS CURVE)
                dbc.Card(dbc.CardBody([
                    html.H6("Development Path (1960-2024)", className="card-subtitle text-primary fw-bold small mb-1"),
                    html.P(id="trajectory-description", className="small text-muted mb-2"),
                    
                    dcc.Graph(id='corr-trajectory-graph', style={'height': '250px'}),
                    
                    html.Small("Log-Log scale used to visualize development stages.", className="text-muted d-block text-end mt-1")
                ]), className="shadow-sm mb-3"),

                # 3. ADVANCED ANALYSIS BUTTON
                dbc.Card(dbc.CardBody([
                    html.H6("Deep Dive Analysis", className="card-subtitle text-primary fw-bold small mb-2"),
                    html.P(id="advanced-analysis-description", className="small text-secondary"),
                    dbc.Button(
                        id="corr-open-advanced-text",
                        children="Open Analysis",
                        color="dark",
                        outline=False,
                        className="w-100 shadow-sm",
                        size="md",
                        n_clicks=0
                    )
                ]), className="shadow-sm"),
                
            ], width=4),
        ]),
        
        # -------------------------------------------------------------
        # MODAL FOR ADVANCED ANALYSIS (DECOUPLING / LIFE PROGRESS)
        # -------------------------------------------------------------
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
            dbc.ModalBody([
                # Explanatory text inside the modal
                html.H6(id="modal-subtitle", className="text-primary fw-bold"),
                html.P(id="modal-description", className="text-muted small mb-4"),
                
                dcc.Graph(id="corr-decoupling-graph"),
                
                # Top countries section
                html.Div(id="top-countries-section", className="mt-4"),
            ]),
            dbc.ModalFooter(
                dbc.Button("Close Analysis", id="corr-close-advanced", color="secondary", size="sm")
            ),
        ], id="corr-modal-advanced", size="xl", centered=True, is_open=False),

        # Hidden Store to keep track of the selected country (ISO code)
        dcc.Store(id="corr-selected-iso-store", data=None),
    ])


# -----------------------------------------------------------------------------
# CALLBACK: TOGGLE BUTTON VIEW MODE
# -----------------------------------------------------------------------------
@callback(
    [Output("view-mode-store", "data"),
     Output("btn-view-gdp", "color"),
     Output("btn-view-life", "color")],
    [Input("btn-view-gdp", "n_clicks"),
     Input("btn-view-life", "n_clicks")],
    prevent_initial_call=False
)
def toggle_view_mode(n_gdp, n_life):
    """Toggle between GDP and Life Expectancy views"""
    trigger = ctx.triggered_id if ctx.triggered else None
    
    if trigger == "btn-view-life":
        return "life", "outline-primary", "primary"
    else:
        return "gdp", "primary", "outline-primary"


# -----------------------------------------------------------------------------
# CALLBACK: UPDATE TITLE AND DESCRIPTION
# -----------------------------------------------------------------------------
@callback(
    [Output("bubble-chart-title", "children"),
     Output("bubble-chart-description", "children"),
     Output("stats-description", "children"),
     Output("trajectory-description", "children"),
     Output("advanced-analysis-description", "children"),
     Output("corr-open-advanced-text", "children")],
    Input("view-mode-store", "data")
)
def update_chart_header(view_mode):
    """Update the chart title and description based on view mode"""
    if view_mode == "life":
        title = "Life Expectancy vs. CO₂ Per Capita (Global Correlation)"
        description = [
            "This chart shows the relationship between Life Expectancy and CO₂ Emissions per Capita. Larger bubbles represent larger populations. ",
            html.Span("Click on a bubble", className="fw-bold text-dark bg-light px-1 rounded"),
            " to trace its development path on the right."
        ]
        stats_desc = "The Pearson Correlation (r) measures how tightly Life Expectancy and Emissions per capita are linked (scale -1 to 1). A positive value indicates that higher emissions per person correlate with longer life expectancy, often due to economic development and healthcare access."
        trajectory_desc = "Visualizing the country's journey in life expectancy and emissions per capita. Is development improving health?"
        advanced_desc = "Analyze health progress: Are countries improving life expectancy while reducing emissions per capita?"
        button_text = "Open Health Progress Analysis"
    else:
        title = "Wealth vs. CO₂ Emissions (Global Correlation)"
        description = [
            "Does economic prosperity require higher emissions? This chart plots Wealth (GDP per Capita) against Pollution (CO₂ per Capita). Larger bubbles represent larger populations. ",
            html.Span("Click on a bubble", className="fw-bold text-dark bg-light px-1 rounded"),
            " to trace its development path on the right."
        ]
        stats_desc = "The Pearson Correlation (r) measures how tightly Wealth and Emissions are linked (scale -1 to 1). A high positive value (near 1.0) indicates 'Coupled' growth: being richer forces you to be dirtier. Lower or negative values signal a global shift towards cleaner technologies."
        trajectory_desc = "Visualizing the country's journey. Are they turning the curve?"
        advanced_desc = "Analyze the 'Decoupling' phenomenon: Is it possible to grow the GDP while reducing emissions?"
        button_text = "Open Decoupling Analysis"
    
    return title, description, stats_desc, trajectory_desc, advanced_desc, button_text


# -----------------------------------------------------------------------------
# 2. CALLBACK: MAIN BUBBLE CHART & STATS
# -----------------------------------------------------------------------------
@callback(
    [Output("corr-bubble-graph", "figure"),
     Output("corr-value-display", "children"),
     Output("corr-explanation-display", "children")],
    Input("tabs", "active_tab"),
    Input("year-slider", "value"),
    Input("corr-selected-iso-store", "data"),
    Input("view-mode-store", "data")
)
def update_bubble_chart(active_tab, selected_year, selected_iso, view_mode):
    if active_tab != "tab-3" or selected_year is None:
        return go.Figure(), "---", ""

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        return create_life_expectancy_chart(selected_year, selected_iso)
    
    # --- GDP VIEW ---
    # Use precomputed merge from prepare_data to avoid repeating heavy joins
    dff = tab3_get_gdp_bubble_year_df(selected_year)

    if dff.empty:
        return go.Figure().update_layout(title="No data"), "N/A", "No data"

    # --- CALCULATE STATISTICS (Pearson Correlation on Log-Log data) ---
    # We use log because economic/emission relationships often follow power laws.
    x_log = np.log10(dff["GDP_pc"])
    y_log = np.log10(dff["CO2_pc"])
    corr = np.corrcoef(x_log, y_log)[0, 1]
    
    # Generate dynamic text explanation
    if corr > 0.7: text_expl = "Strong positive link: Richer = Dirtier"
    elif corr > 0.4: text_expl = "Moderate link"
    elif corr > 0: text_expl = "Weak link"
    else: text_expl = "Decoupled or Inverse relationship!"

    # --- GENERATE CHART ---
    # We pass 'custom_data=["ISOcode"]' to allow click events to identify the country
    fig = px.scatter(
        dff,
        x="GDP_pc",
        y="CO2_pc",
        size="Population",    
        color="Region",       
        hover_name="Country",
        size_max=60,      
        template="plotly_white",
        log_x=True, 
        log_y=True,
        custom_data=["ISOcode"]  # Critical for interactivity
    )

    # Global trend line in log-log space (visual indicator of correlation)
    # Fit: log10(CO2_pc) = a * log10(GDP_pc) + b
    coeffs = np.polyfit(x_log, y_log, 1)
    x_range = np.linspace(x_log.min(), x_log.max(), 100)
    y_trend_log = coeffs[0] * x_range + coeffs[1]
    fig.add_scatter(
        x=10 ** x_range,
        y=10 ** y_trend_log,
        mode="lines",
        line=dict(color="black", width=2, dash="dash"),
        name=f"Global Trend (r={corr:.2f})",
        showlegend=True,
    )

    # Highlight selected country with a ring
    add_selection_ring(fig, dff, selected_iso, "GDP_pc", "CO2_pc")

    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"),
        xaxis_title="GDP per Capita (USD) [Log Scale]",
        yaxis_title="CO₂ per Capita (Tonnes) [Log Scale]",
    )

    return fig, f"{corr:.2f}", text_expl


def create_life_expectancy_chart(selected_year, selected_iso):
    """Create the life expectancy vs CO2 bubble chart using precomputed merges."""
    # Use centralized merge prepared in prepare_data
    df_merged = tab3_get_life_bubble_year_df(selected_year)

    if df_merged.empty:
        return go.Figure().update_layout(title="No data available"), "N/A", "No data"
    
    # Color palette by World Bank region
    color_map = TAB3_LIFE_REGION_COLOR_MAP
    
    # Bubble chart
    fig_bubble = px.scatter(
        df_merged,
        x='Value_capita',
        y='Life_Expectancy',
        size='Population_Proxy',
        color='Region',
        hover_name='Country',
        hover_data={
            'Value_capita': ':.3f',
            'Life_Expectancy': ':.2f',
            'Population_Proxy': False,
            'Region': True
        },
        color_discrete_map=color_map,
        size_max=60,
        log_x=True,
        labels={
            'Value_capita': 'CO2 Per Capita (t/persona)',
            'Life_Expectancy': 'Life Expectancy (years)',
            'Population_Proxy': 'Estimated population'
        },
        custom_data=[df_merged['ISOcode']]
    )
    
    # Global linear fit computed on log10(CO2 per-capita)
    x_log = np.log10(df_merged['Value_capita'])
    y = df_merged['Life_Expectancy']
    
    # Linear fit
    coeffs = np.polyfit(x_log, y, 1)
    x_range = np.linspace(x_log.min(), x_log.max(), 100)
    y_trend = coeffs[0] * x_range + coeffs[1]
    
    # Pearson correlation (r)
    correlation = np.corrcoef(x_log, y)[0, 1]
    
    # Add global trend line
    fig_bubble.add_scatter(
        x=10**x_range,
        y=y_trend,
        mode='lines',
        line=dict(color='black', width=2, dash='dash'),
        name=f'Global Trend (r={correlation:.2f})',
        showlegend=True
    )
    
    # Highlight selected country with a ring
    add_selection_ring(fig_bubble, df_merged, selected_iso, "Value_capita", "Life_Expectancy")
    
    # Layout styling
    fig_bubble.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
        xaxis_title='CO₂ Per Capita (t/person) [Log Scale]',
        yaxis_title='Life Expectancy (years)',
        hovermode='closest',
        legend=dict(
            title="Region",
            orientation="h",
            y=1.02,
            x=0,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        template="plotly_white"
    )
    
    # Generate explanation text
    if correlation > 0.5:
        text_expl = "Positive correlation: Higher CO2 → Longer life"
    elif correlation > 0.2:
        text_expl = "Weak positive link"
    elif correlation > -0.2:
        text_expl = "No clear relationship"
    else:
        text_expl = "Negative correlation detected"
    
    return fig_bubble, f"{correlation:.2f}", text_expl


# -----------------------------------------------------------------------------
# 3. CALLBACK: TRAJECTORY GRAPH (RIGHT PANEL)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-trajectory-graph", "figure"),
    Input("tabs", "active_tab"),
    Input("corr-selected-iso-store", "data"),
    Input("view-mode-store", "data")
)
def update_trajectory(active_tab, selected_iso, view_mode):
    if active_tab != "tab-3":
        return go.Figure()
    
    # If no country selected, show a prompt
    if not selected_iso:
        return go.Figure().update_layout(
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Select a country on the left", "showarrow": False, "font": {"size": 14}}],
            template="plotly_white"
        )
    
    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        # Pre-merged dataset (CO2 pc + Life Expectancy) prepared in prepare_data
        df_country = tab3_get_life_country_trajectory_df(selected_iso)
        
        if df_country.empty:
            return go.Figure().update_layout(
                xaxis={"visible": False}, yaxis={"visible": False},
                annotations=[{"text": "No data for this country", "showarrow": False, "font": {"size": 14}}],
                template="plotly_white"
            )
        
        name = df_country["Country"].iloc[0] if not df_country.empty else selected_iso
        
        fig = go.Figure()
        
        # Draw the path
        fig.add_trace(go.Scatter(
            x=df_country["Value_capita"],
            y=df_country["Life_Expectancy"],
            mode="lines+markers",
            marker=dict(size=6, color=df_country["Year"], colorscale="Viridis", showscale=False),
            line=dict(color="#2c3e50", width=1.5),
            text=df_country["Year"],
            hovertemplate="<b>%{text}</b><br>CO₂ pc: %{x:.2f}t<br>Life Exp: %{y:.1f} years<extra></extra>"
        ))
        
        # Add Start/End annotations
        if len(df_country) > 0:
            # Start
            fig.add_annotation(
                x=np.log10(df_country["Value_capita"].iloc[0]), 
                y=df_country["Life_Expectancy"].iloc[0],
                text=str(int(df_country["Year"].iloc[0])), 
                showarrow=True, arrowhead=1, ax=20, ay=20, bgcolor="white"
            )
            # End
            fig.add_annotation(
                x=np.log10(df_country["Value_capita"].iloc[-1]), 
                y=df_country["Life_Expectancy"].iloc[-1],
                text=str(int(df_country["Year"].iloc[-1])), 
                showarrow=True, arrowhead=1, ax=-20, ay=-20, bgcolor="white", font=dict(weight="bold")
            )
        
        fig.update_layout(
            title=f"{name}",
            template="plotly_white",
            margin={"r": 10, "t": 30, "l": 10, "b": 10},
            xaxis=dict(title="CO₂ per capita (t)", type="log"),
            yaxis=dict(title="Life Expectancy (years)"),
            height=250
        )
        return fig
    
    # --- GDP VIEW (ORIGINAL) ---
    # Pre-merged dataset (GDP pc + CO2 pc) prepared in prepare_data
    df_country = tab3_get_gdp_country_trajectory_df(selected_iso)
    name = df_country["Country"].iloc[0] if not df_country.empty else selected_iso

    fig = go.Figure()

    # Draw the path
    fig.add_trace(go.Scatter(
        x=df_country["GDP_pc"],
        y=df_country["CO2_pc"],
        mode="lines+markers",
        marker=dict(size=6, color=df_country["Year"], colorscale="Viridis", showscale=False),
        line=dict(color="#2c3e50", width=1.5),
        text=df_country["Year"],
        hovertemplate="<b>%{text}</b><br>GDP: $%{x:,.0f}<br>CO2: %{y:.2f}t<extra></extra>"
    ))

    # Add Start/End annotations for clarity
    if not df_country.empty:
        # Start
        fig.add_annotation(
            x=np.log10(df_country["GDP_pc"].iloc[0]), 
            y=np.log10(df_country["CO2_pc"].iloc[0]),
            text=str(df_country["Year"].iloc[0]), 
            showarrow=True, arrowhead=1, ax=20, ay=20, bgcolor="white"
        )
        # End
        fig.add_annotation(
            x=np.log10(df_country["GDP_pc"].iloc[-1]), 
            y=np.log10(df_country["CO2_pc"].iloc[-1]),
            text=str(df_country["Year"].iloc[-1]), 
            showarrow=True, arrowhead=1, ax=-20, ay=-20, bgcolor="white", font=dict(weight="bold")
        )

    fig.update_layout(
        title=f"{name}", # Simple title with country name
        template="plotly_white",
        margin={"r": 10, "t": 30, "l": 10, "b": 10},
        xaxis=dict(title="GDP pc ($)", type="log"),
        yaxis=dict(title="CO2 pc (t)", type="log"),
        height=250
    )
    return fig


# -----------------------------------------------------------------------------
# 4. CALLBACK: MODAL LOGIC (OPEN/CLOSE)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-modal-advanced", "is_open"),
    [Input("corr-open-advanced-text", "n_clicks"), Input("corr-close-advanced", "n_clicks")],
    [State("corr-modal-advanced", "is_open")],
)
def toggle_corr_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


# -----------------------------------------------------------------------------
# 5. CALLBACK: DECOUPLING/LIFE PROGRESS ANALYSIS CHART
# -----------------------------------------------------------------------------
@callback(
    [Output("corr-decoupling-graph", "figure"),
     Output("modal-title", "children"),
     Output("modal-subtitle", "children"),
     Output("modal-description", "children"),
     Output("top-countries-section", "children")],
    Input("corr-modal-advanced", "is_open"),
    Input("year-slider", "value"),
    Input("view-mode-store", "data")
)
def update_advanced_analysis_chart(is_open, selected_year, view_mode):
    if not is_open or selected_year is None:
        return go.Figure(), "", "", "", None
    
    # --- LIFE EXPECTANCY PROGRESS ANALYSIS ---
    if view_mode == "life":
        return create_life_progress_analysis(selected_year)
    
    # --- GDP DECOUPLING ANALYSIS (ORIGINAL) ---
    return create_decoupling_analysis(selected_year)


def create_decoupling_analysis(selected_year):
    """Create the GDP decoupling analysis chart"""
    modal_title = "Decoupling Analysis: Breaking the Link"
    modal_subtitle = "Green Growth vs. Dirty Growth"
    modal_description = "Are we breaking the link between money and smoke? This chart compares the % Growth of GDP (Horizontal) vs. the % Growth of Emissions (Vertical) over time. The goal is the 'Green Growth' zone (Bottom-Right): This represents 'Absolute Decoupling', where an economy grows richer while simultaneously reducing its environmental footprint."

    s_year = 1970
    
    if selected_year <= s_year:
        return create_baseline_figure(s_year, "Relative decoupling data processing starts from this point.<br>Move the slider forward to analyze historical shifts."), modal_title, modal_subtitle, modal_description, None
    
    # --- DATA PREP ---
    df_delta = tab3_get_decoupling_delta(selected_year, start_year=s_year)

    if df_delta is None:
        # Defensive: should be handled by the baseline check above
        return create_baseline_figure(s_year, "Relative decoupling data processing starts from this point.<br>Move the slider forward to analyze historical shifts."), modal_title, modal_subtitle, modal_description, None

    if df_delta.empty:
        return go.Figure().update_layout(title="No shared data"), modal_title, modal_subtitle, modal_description, None

    # --- PLOT GENERATION ---
    fig = px.scatter(
        df_delta, x="dGDP", y="dCO2", color="Region", hover_name="Country",
        title=f"Decoupling Analysis: {s_year} vs {selected_year}",
        template="plotly_white", height=450
    )
    
    # Add reference lines and colored zones
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    
    add_quadrant_zones(fig, [
        {"x0": 0, "x1": 400, "y0": -100, "y1": 0, "color": "green",
         "label": "GREEN GROWTH", "label_x": 50, "label_y": -20, "label_size": 14},
        {"x0": 0, "x1": 400, "y0": 0, "y1": 400, "color": "orange"}
    ])
    
    fig.update_xaxes(title="GDP Change (%)")
    fig.update_yaxes(title="CO2 Emissions Change (%)")

    # --- TOP / BOTTOM PERFORMERS (TEXT + CARDS) ---
    # We mimic the Life Expectancy modal: show who best achieved "green growth"
    # and who experienced the most "dirty growth".
    df_rank = df_delta.copy()

    # A simple composite score: higher GDP growth and lower (ideally negative) CO2 growth
    # increases the score. (Negative dCO2 is rewarded.)
    df_rank["Decoupling_Score"] = df_rank["dGDP"] - (df_rank["dCO2"] / 2)

    # Best: absolute decoupling (GDP up, CO2 down). Fallback to overall score.
    green_zone = df_rank[(df_rank["dGDP"] > 0) & (df_rank["dCO2"] < 0)].copy()
    top_green = (green_zone if not green_zone.empty else df_rank).nlargest(
        5, "Decoupling_Score"
    )[["Country", "dGDP", "dCO2", "Decoupling_Score"]]

    # Worst: coupled growth (GDP up, CO2 up) with the highest CO2 growth. Fallback to low score.
    dirty_zone = df_rank[(df_rank["dGDP"] > 0) & (df_rank["dCO2"] > 0)].copy()
    bottom_dirty = (dirty_zone if not dirty_zone.empty else df_rank).nlargest(
        5, "dCO2"
    )[["Country", "dGDP", "dCO2", "Decoupling_Score"]]

    def format_gdp_metrics(row):
        return [
            f"GDP: {row['dGDP']:+.0f}% | ",
            html.Span(
                f"CO₂: {row['dCO2']:+.0f}%",
                className="text-success" if row["dCO2"] < 0 else "text-danger",
            ),
            html.Span(f" | Score: {row['Decoupling_Score']:.1f}", className="text-muted"),
        ]

    top_section = html.Div([
        html.Hr(className="my-4"),
        html.H6("What does this mean?", className="text-primary fw-bold mb-2"),
        html.P(
            [
                "Countries in the ",
                html.Span("Green Growth", className="fw-bold"),
                " zone (bottom-right) increased GDP while reducing emissions — the strongest form of decoupling.",
                " The cards below highlight best and worst performers for the selected period.",
            ],
            className="text-muted small mb-3",
        ),
        create_ranking_html(
            top_green,
            bottom_dirty,
            "🌿 GREEN GROWTH (ABSOLUTE DECOUPLING)",
            "🔥 COUPLED / DIRTY GROWTH",
            format_gdp_metrics,
        ),
        html.Small(
            "Note: The score is a simple composite (GDP% − CO₂%/2) to rank countries within this view.",
            className="text-muted d-block mt-2",
        ),
    ])

    return fig, modal_title, modal_subtitle, modal_description, top_section


def create_life_progress_analysis(selected_year):
    """Create the Life Expectancy progress analysis chart"""
    modal_title = "Health Progress Analysis: Life vs. Emissions"
    modal_subtitle = "Sustainable Health Improvement"
    modal_description = "Are countries improving health outcomes while managing emissions? This chart compares the Change in Life Expectancy (Horizontal) vs. the Change in CO₂ per Capita (Vertical). The goal is the 'Sustainable Progress' zone (Top-Right): countries that significantly increased life expectancy while reducing or moderately increasing emissions per capita."
    
    s_year = 1970
    
    if selected_year <= s_year:
        return create_baseline_figure(s_year, "Progress analysis starts from this point.<br>Move the slider forward to analyze health improvements."), modal_title, modal_subtitle, modal_description, None
    
    # --- DATA PREP ---
    df_delta = tab3_get_life_progress_delta(selected_year, start_year=s_year)

    if df_delta is None:
        # Defensive: should be handled by the baseline check above
        return create_baseline_figure(s_year, "Progress analysis starts from this point.<br>Move the slider forward to analyze health improvements."), modal_title, modal_subtitle, modal_description, None

    if df_delta.empty:
        return go.Figure().update_layout(title="No shared data"), modal_title, modal_subtitle, modal_description, None
    
    # --- PLOT GENERATION ---
    fig = px.scatter(
        df_delta, x="dLife", y="dCO2", color="Region", hover_name="Country",
        title=f"Health Progress Analysis: {s_year} vs {selected_year}",
        template="plotly_white", height=450
    )
    
    # Add reference lines and colored zones
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    
    add_quadrant_zones(fig, [
        {"x0": 0, "x1": 40, "y0": -100, "y1": 0, "color": "green",
         "label": "SUSTAINABLE PROGRESS", "label_x": 15, "label_y": -30, "label_size": 12},
        {"x0": 0, "x1": 40, "y0": 0, "y1": 400, "color": "orange",
         "label": "HIGH COST PROGRESS", "label_x": 15, "label_y": 100, "label_size": 11}
    ])
    
    fig.update_xaxes(title="Life Expectancy Change (years)")
    fig.update_yaxes(title="CO₂ per Capita Change (%)")
    
    # Sustainability score is precomputed in prepare_data.tab3_get_life_progress_delta

    # Get top 5 most sustainable and least sustainable
    top_sustainable = df_delta.nlargest(5, "Sustainability_Score")[["Country", "dLife", "dCO2", "Sustainability_Score"]]
    least_sustainable = df_delta.nsmallest(5, "Sustainability_Score")[["Country", "dLife", "dCO2", "Sustainability_Score"]]
    
    # Create HTML component with top countries using unified function
    def format_life_metrics(row):
        return [
            f"Life: +{row['dLife']:.1f} years | ",
            html.Span(f"CO₂: {row['dCO2']:.0f}%", 
                     className="text-success" if row['dCO2'] < 0 else "text-warning")
        ]
    
    top_section = create_ranking_html(
        top_sustainable, least_sustainable,
        "🌿 SUSTAINABLE PROGRESS", "⚠️ HIGH COST PROGRESS",
        format_life_metrics
    )
    
    return fig, modal_title, modal_subtitle, modal_description, top_section


# -----------------------------------------------------------------------------
# 6. CALLBACK: HANDLE CLICKS (INTERACTIVITY)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-selected-iso-store", "data"),
    Input("corr-bubble-graph", "clickData"),
    prevent_initial_call=False
)
def update_corr_country_store(clickData):
    """
    Updates the selected country store when a bubble is clicked.
    Uses 'customdata' to retrieve the robust ISO code.
    """
    if clickData and clickData.get("points"):
        # Retrieve ISO code stored in customdata[0]
        try:
            return clickData["points"][0]["customdata"][0]
        except:
            return None
    return None
