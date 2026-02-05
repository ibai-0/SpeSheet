from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from prepare_data import df_totals, df_capita, df_gdp_total, df_gdp_capita, min_year, max_year, ISO_TO_REGION
from components import controls

def layout():
    return html.Div(className='tab-animacion', children=[
        
        # --- CONTROL BAR (Year Slider & Region Filter) ---
        controls.layout(),

        dbc.Row([
            # -------------------------------------------------------------
            # LEFT COLUMN: MAIN BUBBLE CHART 
            # -------------------------------------------------------------
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    # Title and Context for the user
                    html.H5("Wealth vs. CO₂ Emissions (Global Correlation)", className="text-primary fw-bold mb-1"),
                    html.P([
                        "Does economic prosperity require higher emissions? This chart plots Wealth (GDP per Capita) against Pollution (CO₂ per Capita). Larger bubbles represent larger populations. ",
                        html.Span("Click on a bubble", className="fw-bold text-dark bg-light px-1 rounded"),
                        " to trace its development path on the right."
                    ], className="text-muted small mb-3"),
                    
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
                    html.P("The Pearson Correlation (r) measures how tightly Wealth and Emissions are linked (scale -1 to 1). A high positive value (near 1.0) indicates 'Coupled' growth: being richer forces you to be dirtier. Lower or negative values signal a global shift towards cleaner technologies.", className="small text-secondary mb-2"),
                    
                    # Dynamic Values
                    html.H2(id="corr-value-display", className="text-center my-2 fw-bold text-dark"),
                    html.P(id="corr-explanation-display", className="text-center text-muted small mb-0")
                ]), className="shadow-sm mb-3"),

                # 2. TRAJECTORY GRAPH (KUZNETS CURVE)
                dbc.Card(dbc.CardBody([
                    html.H6("Development Path (1960-2024)", className="card-subtitle text-primary fw-bold small mb-1"),
                    html.P("Visualizing the country's journey. Are they turning the curve?", className="small text-muted mb-2"),
                    
                    dcc.Graph(id='corr-trajectory-graph', style={'height': '250px'}),
                    
                    html.Small("Log-Log scale used to visualize development stages.", className="text-muted d-block text-end mt-1")
                ]), className="shadow-sm mb-3"),

                # 3. ADVANCED ANALYSIS BUTTON
                dbc.Card(dbc.CardBody([
                    html.H6("Deep Dive Analysis", className="card-subtitle text-primary fw-bold small mb-2"),
                    html.P("Analyze the 'Decoupling' phenomenon: Is it possible to grow the GDP while reducing emissions?", className="small text-secondary"),
                    dbc.Button(
                        "Open Decoupling Analysis",
                        id="corr-open-advanced",
                        color="dark",
                        outline=False,
                        className="w-100 shadow-sm",
                        size="md"
                    )
                ]), className="shadow-sm"),
                
            ], width=4),
        ]),
        
        # -------------------------------------------------------------
        # MODAL FOR ADVANCED ANALYSIS (DECOUPLING)
        # -------------------------------------------------------------
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Decoupling Analysis: Breaking the Link")),
            dbc.ModalBody([
                # Explanatory text inside the modal
                html.H6("Green Growth vs. Dirty Growth", className="text-primary fw-bold"),
                html.P("Are we breaking the link between money and smoke? This chart compares the % Growth of GDP (Horizontal) vs. the % Growth of Emissions (Vertical) over time. The goal is the 'Green Growth' zone (Bottom-Right): This represents 'Absolute Decoupling', where an economy grows richer while simultaneously reducing its environmental footprint.", 
                       className="text-muted small mb-4"),
                
                dcc.Graph(id="corr-decoupling-graph"),
            ]),
            dbc.ModalFooter(
                dbc.Button("Close Analysis", id="corr-close-advanced", color="secondary", size="sm")
            ),
        ], id="corr-modal-advanced", size="xl", centered=True, is_open=False),

        # Hidden Store to keep track of the selected country (ISO code)
        dcc.Store(id="corr-selected-iso-store", data=None),
    ])


# -----------------------------------------------------------------------------
# 1. DATA PREPARATION HELPER
# -----------------------------------------------------------------------------
def _get_merged_data():
    """
    Merges CO2 Per Capita, GDP Per Capita, and CO2 Total into a single DataFrame.
    Calculates Population (approx) and maps Regions.
    """
    co2 = df_capita.rename(columns={"Value": "CO2_pc"})[["ISOcode", "Country", "Year", "CO2_pc"]]
    gdp = df_gdp_capita.rename(columns={"Value": "GDP_pc"})[["ISOcode", "Year", "GDP_pc"]]
    co2_tot = df_totals.rename(columns={"Value": "CO2_total"})[["ISOcode", "Year", "CO2_total"]]

    # Inner join to ensure we have all metrics for the points
    df = pd.merge(co2, gdp, on=["ISOcode", "Year"], how="inner")
    df = pd.merge(df, co2_tot, on=["ISOcode", "Year"], how="inner")

    # Calculate Population for bubble size
    df["Population"] = df["CO2_total"] / df["CO2_pc"]
    
    # Map ISO codes to Regions (for coloring)
    df["Region"] = df["ISOcode"].map(ISO_TO_REGION).fillna("Other")

    df = df.dropna(subset=["CO2_pc", "GDP_pc"])
    # Filter out non-positive values to avoid Log Scale errors
    df = df[(df["CO2_pc"] > 0) & (df["GDP_pc"] > 0)]
    
    return df


# -----------------------------------------------------------------------------
# 2. CALLBACK: MAIN BUBBLE CHART & STATS
# -----------------------------------------------------------------------------
@callback(
    [Output("corr-bubble-graph", "figure"),
     Output("corr-value-display", "children"),
     Output("corr-explanation-display", "children")],
    Input("tabs", "active_tab"),
    Input("year-slider", "value"),
    Input("corr-selected-iso-store", "data")
)
def update_bubble_chart(active_tab, selected_year, selected_iso):
    if active_tab != "tab-3" or selected_year is None:
        return go.Figure(), "---", ""

    df = _get_merged_data()
    dff = df[df["Year"] == selected_year].copy()

    if dff.empty:
        return go.Figure().update_layout(title="No data"), "N/A", "No data"

    # --- CALCULATE STATISTICS (Pearson Correlation on Log-Log data) ---
    # We use Log because economic/emission relationships follow power laws
    corr = np.corrcoef(np.log10(dff["GDP_pc"]), np.log10(dff["CO2_pc"]))[0, 1]
    
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

    # Highlight selected country with a ring
    if selected_iso:
        selected = dff[dff["ISOcode"] == selected_iso]
        if not selected.empty:
            fig.add_trace(go.Scatter(
                x=selected["GDP_pc"],
                y=selected["CO2_pc"],
                mode='markers',
                marker=dict(size=20, color='rgba(0,0,0,0)', symbol='circle', line=dict(width=3, color='black')),
                showlegend=False,
                hoverinfo='skip'
            ))

    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"),
        xaxis_title="GDP per Capita (USD) [Log Scale]",
        yaxis_title="CO₂ per Capita (Tonnes) [Log Scale]",
    )

    return fig, f"{corr:.2f}", text_expl


# -----------------------------------------------------------------------------
# 3. CALLBACK: TRAJECTORY GRAPH (RIGHT PANEL)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-trajectory-graph", "figure"),
    Input("tabs", "active_tab"),
    Input("corr-selected-iso-store", "data")
)
def update_trajectory(active_tab, selected_iso):
    if active_tab != "tab-3":
        return go.Figure()

    df = _get_merged_data()
    
    # If no country selected, show a prompt
    if not selected_iso:
        return go.Figure().update_layout(
            # title="Click on a bubble to see history", <-- Title handled in HTML now
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Select a country on the left", "showarrow": False, "font": {"size": 14}}],
            template="plotly_white"
        )
    
    # Filter data for the specific country history
    df_country = df[df["ISOcode"] == selected_iso].sort_values("Year")
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
    [Input("corr-open-advanced", "n_clicks"), Input("corr-close-advanced", "n_clicks")],
    [State("corr-modal-advanced", "is_open")],
)
def toggle_corr_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


# -----------------------------------------------------------------------------
# 5. CALLBACK: DECOUPLING ANALYSIS CHART
# -----------------------------------------------------------------------------
@callback(
    Output("corr-decoupling-graph", "figure"),
    Input("corr-modal-advanced", "is_open"),
    Input("year-slider", "value")
)
def update_decoupling_chart(is_open, selected_year):
    if not is_open or selected_year is None:
        return go.Figure()

    # --- YEAR LOGIC ---
    # Determine the start year (base). Decoupling is relative, so we need a prior year to compare.
    s_year = 1970 
    
    if selected_year <= s_year:
         return go.Figure().update_layout(
             template="plotly_white",
             xaxis={"visible": False}, yaxis={"visible": False},
             annotations=[{
                 "text": f"<b>Baseline Year: {s_year}</b><br>Relative decoupling data processing starts from this point.<br>Move the slider forward to analyze historical shifts.", 
                 "showarrow": False, "font": {"size": 16, "color": "gray"}
             }]
         )

    # --- DATA AGGREGATION ---
    # Group by ISO to handle duplicate rows if any, and ensure we match countries correctly
    # We cast to string to avoid index type mismatch issues
    
    # CO2 Start & End
    d_c_start = df_totals[df_totals["Year"] == s_year].copy()
    d_c_start["ISOcode"] = d_c_start["ISOcode"].astype(str)
    s_c_start = d_c_start.groupby("ISOcode")["Value"].sum()
    
    d_c_end = df_totals[df_totals["Year"] == selected_year].copy()
    d_c_end["ISOcode"] = d_c_end["ISOcode"].astype(str)
    s_c_end = d_c_end.groupby("ISOcode")["Value"].sum()

    # GDP Start & End
    d_g_start = df_gdp_total[df_gdp_total["Year"] == s_year].copy()
    d_g_start["ISOcode"] = d_g_start["ISOcode"].astype(str)
    s_g_start = d_g_start.groupby("ISOcode")["Value"].sum()
    
    d_g_end = df_gdp_total[df_gdp_total["Year"] == selected_year].copy()
    d_g_end["ISOcode"] = d_g_end["ISOcode"].astype(str)
    s_g_end = d_g_end.groupby("ISOcode")["Value"].sum()

    # --- MERGE DATA ---
    # Use concat on axis=1 to align all series by ISO index
    df_delta = pd.concat(
        [s_c_start, s_c_end, s_g_start, s_g_end], 
        axis=1, 
        keys=["CO2_s", "CO2_e", "GDP_s", "GDP_e"]
    ).dropna()

    if df_delta.empty:
        return go.Figure().update_layout(title="No shared data")

    # --- CALCULATE GROWTH RATES (%) ---
    # Filter out zero values to avoid division by zero
    df_delta = df_delta[(df_delta["CO2_s"] != 0) & (df_delta["GDP_s"] != 0)]
    
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100
    df_delta["dGDP"] = ((df_delta["GDP_e"] / df_delta["GDP_s"]) - 1) * 100
    
    # --- RECOVER COUNTRY NAMES ---
    # Create a reference map from the original dataset: ISO -> Country Name
    iso_map = df_totals.groupby("ISOcode")["Country"].first().to_dict()
    
    # Map the index (ISO) to the Name
    df_delta["Country"] = df_delta.index.map(iso_map)
    # Fallback to ISO code if name is missing
    df_delta["Country"] = df_delta["Country"].fillna(df_delta.index.to_series())

    # Map Regions for coloring
    df_delta["Region"] = df_delta.index.map(ISO_TO_REGION).fillna("Other")

    # --- VISUAL FILTERS ---
    # Remove extreme outliers that would flatten the chart
    df_delta = df_delta[(df_delta["dGDP"] < 400) & (df_delta["dGDP"] > -80)]
    df_delta = df_delta[(df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]

    # --- PLOT GENERATION ---
    fig = px.scatter(
        df_delta, 
        x="dGDP", 
        y="dCO2", 
        color="Region",
        hover_name="Country", # Display the recovered full name
        title=f"Decoupling Analysis: {s_year} vs {selected_year}",
        template="plotly_white", 
        height=450
    )
    
    # Add reference lines (0,0)
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    
    # Highlight "Green Growth" Quadrant (Bottom Right)
    fig.add_shape(type="rect", x0=0, x1=400, y0=-100, y1=0, fillcolor="green", opacity=0.1, layer="below", line_width=0)
    fig.add_annotation(x=50, y=-20, text="<b>GREEN GROWTH</b>", showarrow=False, font=dict(color="green", size=14))

    # Highlight "Dirty Growth" Quadrant (Top Right)
    fig.add_shape(type="rect", x0=0, x1=400, y0=0, y1=400, fillcolor="orange", opacity=0.1, layer="below", line_width=0)
    
    fig.update_xaxes(title="GDP Change (%)")
    fig.update_yaxes(title="CO2 Emissions Change (%)")

    return fig


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