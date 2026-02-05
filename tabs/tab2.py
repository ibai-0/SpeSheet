from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from prepare_data import df_gdp_total, df_gdp_capita
from components import controls

def layout():
    return html.Div(className='tab-animacion', children=[
        controls.layout(),
        
        # GDP Stats cards (Top summary cards)
        dbc.Row(id="gdp-stats-container", className="mb-3 g-2"),

        # Controls for GDP view (Radio buttons & Modal Button)
        dbc.Row([
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
            ], className="py-2 px-3"), className="shadow-sm"), width=8), ## here the height Hugow

            dbc.Col(
                dbc.Button("Advanced Prosperity Analysis", id="open-advanced-gdp",
                           color="primary", className="w-100 shadow-sm h-100", size="sm"),
                width=4
            ),
        ], className="mb-2"),

        # --- MAIN SECTION: SPLIT VIEW (MAP LEFT / LINES RIGHT) ---
        dbc.Row([
            # --- LEFT COLUMN: MAP (Takes 8/12 width) ---
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5("Global Economic Landscape", className="text-primary fw-bold mb-1"),
                    html.P([
                        "Geospatial distribution of wealth. ",
                        # Interactive instruction highlighted
                        html.Span("Click on any country", className="fw-bold text-dark bg-light px-1 rounded"), 
                        " to update the historical analysis on the right."
                    ], className="text-muted small mb-2"),
                    
                    dcc.Graph(id="gdp-map")
                ]), className="shadow-sm h-100") # h-100 makes the card full height
            ], width=8),

            # --- RIGHT COLUMN: COUNTRY LINES (Takes 4/12 width) ---
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5("Historical Trajectory", className="text-primary fw-bold mb-1"),
                    html.P("Comparing the selected nation against the Global Average over time (Total & Per Capita).", 
                           className="text-muted small mb-2"),
                    
                    dcc.Graph(id="gdp-country-lines")
                ]), className="shadow-sm h-100")
            ], width=4)

        ], className="mb-3 g-3"), # g-3 adds gap between columns

        # --- MODAL FOR ADVANCED ANALYSIS ---
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Advanced Economic Analysis")),
                dbc.ModalBody([
                    html.P("Deep dive into the economic structure, inequality, and stability of nations for the selected year.", className="text-muted mb-4"),
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

# --- CALLBACK 1: UPDATE STAT CARDS ---
@callback(
    Output("gdp-stats-container", "children"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input('tabs', 'active_tab')
)
def update_gdp_cards(selected_year, view, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return []
        
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
    Output("gdp-map", "figure"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input('tabs', 'active_tab')
)
def update_gdp_map(selected_year, view, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return go.Figure()

    dff = _get_gdp_df(view)
    dff = dff[dff["Year"] == selected_year].dropna(subset=["Value"]).copy()
    dff = dff[dff["Value"] > 0]

    if dff.empty:
        return go.Figure().update_layout(title="No data to show")

    # Log scale is used to visualize differences between massive economies (USA, China) and smaller ones.
    dff["ColorValue"] = np.log10(dff["Value"])

    fig = px.choropleth(
        dff,
        locations="ISOcode",
        color="ColorValue",
        hover_name="Country",
        hover_data={"Value": ":,.2f", "ColorValue": False},
        color_continuous_scale="Viridis",
        height=550 # Increased height to match the side panel
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="log10(GDP)", thickness=15, len=0.6),
        geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
        # Interaction Hint in the layout
        annotations=[dict(
            x=0.5, y=-0.1, xref='paper', yref='paper',
            text="Interactive: Select a country to see details >",
            showarrow=False, font=dict(size=12, color="gray")
        )]
    )
    return fig

# --- CALLBACK 3: UPDATE SIDE LINES (HISTORY) ---
@callback(
    Output("gdp-country-lines", "figure"),
    Input("gdp-map", "clickData"), # Listens to map clicks
    Input("year-slider", "value"),
    Input('tabs', 'active_tab')
)
def update_country_lines(clickData, selected_year, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return go.Figure()

    iso = None
    # Check if user clicked on the map
    if clickData and clickData.get("points"):
        iso = clickData["points"][0].get("location")

    # Fallback: If no country is selected, default to the one with max GDP (e.g., USA)
    dff_y = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    if iso is None and not dff_y.empty:
        iso = dff_y.loc[dff_y["Value"].idxmax(), "ISOcode"]

    if iso is None:
        return go.Figure().update_layout(title="Click on a country")

    # Fetch data for the selected country
    c_total = df_gdp_total[df_gdp_total["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    c_cap = df_gdp_capita[df_gdp_capita["ISOcode"] == iso].dropna(subset=["Value"]).copy()

    # Filter data up to the selected year (so we don't show future if slider is back in time)
    # OR we show full history (better for context). Let's show full history.
    # c_total = c_total[c_total["Year"] <= selected_year] 
    
    name = c_total["Country"].iloc[0] if not c_total.empty else c_cap["Country"].iloc[0]

    # Calculate Global Averages for comparison
    avg_total = df_gdp_total.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_cap = df_gdp_capita.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()

    # Create Subplots: 2 vertical charts
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=(f"Total GDP ({name})", f"GDP per Capita ({name})"),
                        vertical_spacing=0.15)

    # 1. Total GDP Line
    fig.add_trace(go.Scatter(x=c_total["Year"], y=c_total["Value"], mode="lines", name=f"{name} (Total)", line=dict(width=3)),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=avg_total["Year"], y=avg_total["Value"], mode="lines",
                             name="Global Avg", line=dict(color="gray", dash="dash")),
                  row=1, col=1)

    # 2. Per Capita Line
    fig.add_trace(go.Scatter(x=c_cap["Year"], y=c_cap["Value"], mode="lines", name=f"{name} (Per Capita)", line=dict(width=3), showlegend=True),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=avg_cap["Year"], y=avg_cap["Value"], mode="lines",
                             name="Global Avg", line=dict(color="gray", dash="dash"), showlegend=False),
                  row=2, col=1)

    # Add a vertical line to indicate the selected year from the slider
    fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")

    fig.update_layout(
        height=550, # Matched with map height
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified" # Shows all values for that year on hover
    )
    return fig

# --- CALLBACK 4: MODAL OPEN/CLOSE ---
@callback(
    Output("modal-advanced-gdp", "is_open"),
    [Input("open-advanced-gdp", "n_clicks"), Input("close-advanced-gdp", "n_clicks")],
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
    Input('tabs', 'active_tab')
)
def update_advanced_modal_gdp(selected_year, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return None

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