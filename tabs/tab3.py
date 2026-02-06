from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from prepare_data import (df_totals, df_capita, df_gdp_total, df_gdp_capita, min_year, max_year, 
                          ISO_TO_REGION, df_life_expectancy, clean_isocode, aggregate_by_year, 
                          map_countries_regions, CONTINENT_MAP)
from components import controls

def add_selection_ring(fig, df, selected_iso, x_col, y_col):
    """Add selection ring"""
    if selected_iso:
        selected = df[df["ISOcode"] == selected_iso]
        if not selected.empty:
            fig.add_trace(go.Scatter(
                x=selected[x_col], y=selected[y_col], mode='markers',
                marker=dict(size=20, color='rgba(0,0,0,0)', symbol='circle', line=dict(width=3, color='black')),
                showlegend=False, hoverinfo='skip'
            ))
    return fig

def create_baseline_figure(year, message):
    """Placeholder figure for base year"""
    return go.Figure().update_layout(
        template="plotly_white", xaxis={"visible": False}, yaxis={"visible": False},
        annotations=[{"text": f"<b>Base Year: {year}</b><br>{message}", "showarrow": False, "font": {"size": 16, "color": "gray"}}]
    )

def add_quadrant_zones(fig, zones):
    """Add colored quadrant zones"""
    for zone in zones:
        fig.add_shape(type="rect", x0=zone["x0"], x1=zone["x1"], y0=zone["y0"], y1=zone["y1"], 
                     fillcolor=zone["color"], opacity=0.1, layer="below", line_width=0)
        if "label" in zone:
            fig.add_annotation(x=zone["label_x"], y=zone["label_y"], text=f"<b>{zone['label']}</b>", 
                             showarrow=False, font=dict(color=zone["color"], size=zone.get("label_size", 12)))
    return fig

def create_ranking_html(top_df, bottom_df, top_title, bottom_title, metrics_formatter):
    """Create ranking HTML with best and worst"""
    def create_cards(df):
        cards = []
        for i, (idx, row) in enumerate(df.iterrows()):
            cards.append(dbc.Card([dbc.CardBody([
                html.Div([html.Span(f"{i+1}. ", className="fw-bold text-muted me-2"),
                         html.Span(row['Country'], className="fw-bold")]),
                html.Small(metrics_formatter(row), className="text-muted")
            ], className="py-2 px-3")], className="mb-2"))
        return cards
    
    return dbc.Row([
        dbc.Col([html.H6(top_title, className="text-success fw-bold mb-3"),
                 html.Div(create_cards(top_df))], width=6),
        dbc.Col([html.H6(bottom_title, className="text-danger fw-bold mb-3"),
                 html.Div(create_cards(bottom_df))], width=6)
    ])

def layout():
    return html.Div(className='tab-animacion', children=[
        controls.layout(),

        # Toggle buttons
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("GDP", id="btn-view-gdp", color="primary", size="lg", className="px-5"),
                    dbc.Button("Life Expectancy", id="btn-view-life", color="outline-primary", size="lg", className="px-5")
                ], className="mb-3 d-flex justify-content-center w-100")
            ], width=12)
        ], className="mb-3"),

        dcc.Store(id="view-mode-store", data="gdp"),

        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5(id="bubble-chart-title", className="text-primary fw-bold mb-1"),
                    html.P(id="bubble-chart-description", className="text-muted small mb-3"),
                    dcc.Graph(id='corr-bubble-graph', style={'height': '600px'}) 
                ]), className="shadow-sm h-100")
            ], width=8),
            
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H6("Statistics", className="card-subtitle text-muted fw-bold small mb-2"),
                    html.P(id="stats-description", className="small text-secondary mb-2"),
                    html.H2(id="corr-value-display", className="text-center my-2 fw-bold text-dark"),
                    html.P(id="corr-explanation-display", className="text-center text-muted small mb-0")
                ]), className="shadow-sm mb-3"),

                dbc.Card(dbc.CardBody([
                    html.H6("Trajectory (1960-2024)", className="card-subtitle text-primary fw-bold small mb-1"),
                    html.P(id="trajectory-description", className="small text-muted mb-2"),
                    dcc.Graph(id='corr-trajectory-graph', style={'height': '250px'}),
                    html.Small("Log-log scale.", className="text-muted d-block text-end mt-1")
                ]), className="shadow-sm mb-3"),

                dbc.Card(dbc.CardBody([
                    html.H6("Advanced Analysis", className="card-subtitle text-primary fw-bold small mb-2"),
                    html.P(id="advanced-analysis-description", className="small text-secondary"),
                    dbc.Button(id="corr-open-advanced-text", children="Open Analysis", 
                              color="dark", outline=False, className="w-100 shadow-sm", size="md", n_clicks=0)
                ]), className="shadow-sm"),
                
            ], width=4),
        ]),
        
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
            dbc.ModalBody([
                html.H6(id="modal-subtitle", className="text-primary fw-bold"),
                html.P(id="modal-description", className="text-muted small mb-4"),
                dcc.Graph(id="corr-decoupling-graph"),
                html.Div(id="top-countries-section", className="mt-4"),
            ]),
            dbc.ModalFooter(dbc.Button("Close", id="corr-close-advanced", color="secondary", size="sm")),
        ], id="corr-modal-advanced", size="xl", centered=True, is_open=False),

        dcc.Store(id="corr-selected-iso-store", data=None),
    ])


@callback(
    [Output("view-mode-store", "data"),
     Output("btn-view-gdp", "color"),
     Output("btn-view-life", "color")],
    [Input("btn-view-gdp", "n_clicks"),
     Input("btn-view-life", "n_clicks")],
    prevent_initial_call=False
)
def toggle_view_mode(n_gdp, n_life):
    trigger = ctx.triggered_id if ctx.triggered else None
    
    if trigger == "btn-view-life":
        return "life", "outline-primary", "primary"
    else:
        return "gdp", "primary", "outline-primary"

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
    if view_mode == "life":
        title = "Life Expectancy vs. CO2 per Capita"
        description = [
            "Relationship between life expectancy and emissions. ",
            html.Span("Click a bubble", className="fw-bold text-dark bg-light px-1 rounded"),
            " to see the trajectory."
        ]
        stats_desc = "Pearson correlation (r) measures the relationship. Positive value = higher emissions associated with longer life expectancy."
        trajectory_desc = "Country journey in health and emissions."
        advanced_desc = "Analyze progress: does health improve while emissions fall?"
        button_text = "Health Progress Analysis"
    else:
        title = "Wealth vs. CO2 Emissions"
        description = [
            "Does prosperity require more emissions? GDP per capita vs CO2 per capita. ",
            html.Span("Click a bubble", className="fw-bold text-dark bg-light px-1 rounded"),
            " to see the trajectory."
        ]
        stats_desc = "High correlation (+1.0) = coupled growth: grow = pollute. Low values = clean technologies."
        trajectory_desc = "Country journey. Are they bending the curve?"
        advanced_desc = "Analyze 'Decoupling': grow GDP while reducing emissions?"
        button_text = "Decoupling Analysis"
    
    return title, description, stats_desc, trajectory_desc, advanced_desc, button_text

def _get_merged_data():
    """Merge CO2 per Capita, GDP per Capita, and total CO2"""
    co2 = df_capita.rename(columns={"Value": "CO2_pc"})[["ISOcode", "Country", "Year", "CO2_pc"]]
    gdp = df_gdp_capita.rename(columns={"Value": "GDP_pc"})[["ISOcode", "Year", "GDP_pc"]]
    co2_tot = df_totals.rename(columns={"Value": "CO2_total"})[["ISOcode", "Year", "CO2_total"]]

    df = pd.merge(co2, gdp, on=["ISOcode", "Year"], how="inner")
    df = pd.merge(df, co2_tot, on=["ISOcode", "Year"], how="inner")
    df["Population"] = df["CO2_total"] / df["CO2_pc"]
    df["Region"] = df["ISOcode"].map(ISO_TO_REGION).fillna("Other")
    df = df.dropna(subset=["CO2_pc", "GDP_pc"])
    df = df[(df["CO2_pc"] > 0) & (df["GDP_pc"] > 0)]
    return df
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

    if view_mode == "life":
        return create_life_expectancy_chart(selected_year, selected_iso)
    
    df = _get_merged_data()
    dff = df[df["Year"] == selected_year].copy()

    if dff.empty:
        return go.Figure().update_layout(title="No data"), "N/A", "No data"

    corr = np.corrcoef(np.log10(dff["GDP_pc"]), np.log10(dff["CO2_pc"]))[0, 1]
    
    if corr > 0.7: text_expl = "Strong link: rich = dirty"
    elif corr > 0.4: text_expl = "Moderate link"
    elif corr > 0: text_expl = "Weak link"
    else: text_expl = "Decoupled or inverse!"

    fig = px.scatter(dff, x="GDP_pc", y="CO2_pc", size="Population", color="Region", hover_name="Country",
                    size_max=60, template="plotly_white", log_x=True, log_y=True, custom_data=["ISOcode"])

    add_selection_ring(fig, dff, selected_iso, "GDP_pc", "CO2_pc")

    fig.update_layout(margin={"r": 20, "t": 20, "l": 20, "b": 20}, 
                     legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"),
                     xaxis_title="GDP per Capita (USD) [Log]", yaxis_title="CO2 per Capita (Tons) [Log]")

    return fig, f"{corr:.2f}", text_expl


def create_life_expectancy_chart(selected_year, selected_iso):
    """Life expectancy vs CO2 chart"""
    dff_capita = df_capita[df_capita['Year'] == selected_year].copy()
    dff_totals = df_totals[df_totals['Year'] == selected_year].copy()
    dff_life = df_life_expectancy[df_life_expectancy['Year'] == selected_year].copy()
    
    if 'ISOcode' not in dff_life.columns:
        return go.Figure().update_layout(title="Error: ISOcode not found"), "N/A", "Error"
    
    clean_isocode(dff_capita)
    clean_isocode(dff_totals)
    clean_isocode(dff_life)
    
    df_co2_combined = pd.merge(dff_capita, dff_totals[['ISOcode', 'Value']], on='ISOcode', suffixes=('_capita', '_total'))
    df_co2_combined['Population_Proxy'] = np.where(df_co2_combined['Value_capita'] > 0, 
                                                     df_co2_combined['Value_total'] / df_co2_combined['Value_capita'], 1)
    
    df_merged = pd.merge(df_co2_combined, dff_life, on=['ISOcode', 'Year'], how='inner', suffixes=('_co2', '_life'))
    df_merged['Country'] = df_merged['Country_co2']
    df_merged['Continent'] = df_merged['ISOcode'].map(CONTINENT_MAP).fillna('Other')
    df_merged = df_merged[(df_merged['Value_capita'] > 0) & (df_merged['Life_Expectancy'] > 0) & (df_merged['Population_Proxy'] > 0)]
    
    color_map = {'Europe': '#3498db', 'Asia': '#e74c3c', 'America': '#2ecc71', 'Africa': '#f39c12', 'Oceania': '#9b59b6', 'Other': '#95a5a6'}
    
    if df_merged.empty:
        return go.Figure().update_layout(title="No data"), "N/A", "No data"
    
    fig_bubble = px.scatter(df_merged, x='Value_capita', y='Life_Expectancy', size='Population_Proxy', color='Continent',
                            hover_name='Country', hover_data={'Value_capita': ':.3f', 'Life_Expectancy': ':.2f', 
                            'Population_Proxy': False, 'Continent': True}, color_discrete_map=color_map, size_max=60, log_x=True,
                            labels={'Value_capita': 'CO2 per Capita (t/person)', 'Life_Expectancy': 'Life Expectancy (years)', 
                            'Population_Proxy': 'Estimated population'}, custom_data=[df_merged['ISOcode']])
    
    x_log = np.log10(df_merged['Value_capita'])
    y = df_merged['Life_Expectancy']
    coeffs = np.polyfit(x_log, y, 1)
    x_range = np.linspace(x_log.min(), x_log.max(), 100)
    y_trend = coeffs[0] * x_range + coeffs[1]
    correlation = np.corrcoef(x_log, y)[0, 1]
    
    fig_bubble.add_scatter(x=10**x_range, y=y_trend, mode='lines', line=dict(color='black', width=2, dash='dash'),
                          name=f'Trend (r={correlation:.2f})', showlegend=True)
    
    add_selection_ring(fig_bubble, df_merged, selected_iso, "Value_capita", "Life_Expectancy")
    
    fig_bubble.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20}, xaxis_title='CO2 per Capita (t/person) [Log]',
        yaxis_title='Life Expectancy (years)', hovermode='closest',
        legend=dict(title="Continent", orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"), template="plotly_white"
    )
    
    if correlation > 0.5: text_expl = "Positive correlation: higher CO2 -> longer life"
    elif correlation > 0.2: text_expl = "Weak positive correlation"
    elif correlation > -0.2: text_expl = "No clear relationship"
    else: text_expl = "Negative correlation detected"
    
    return fig_bubble, f"{correlation:.2f}", text_expl
@callback(
    Output("corr-trajectory-graph", "figure"),
    Input("tabs", "active_tab"),
    Input("corr-selected-iso-store", "data"),
    Input("view-mode-store", "data")
)
def update_trajectory(active_tab, selected_iso, view_mode):
    if active_tab != "tab-3":
        return go.Figure()
    
    if not selected_iso:
        return go.Figure().update_layout(xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Select a country", "showarrow": False, "font": {"size": 14}}], template="plotly_white")
    
    if view_mode == "life":
        df_co2 = df_capita[df_capita["ISOcode"] == selected_iso].copy()
        df_life = df_life_expectancy[df_life_expectancy["ISOcode"] == selected_iso].copy()
        
        df_country = pd.merge(df_co2, df_life[["Year", "Life_Expectancy"]], on="Year", how="inner").sort_values("Year")
        df_country = df_country[(df_country["Value"] > 0) & (df_country["Life_Expectancy"] > 0)]
        
        if df_country.empty:
            return go.Figure().update_layout(xaxis={"visible": False}, yaxis={"visible": False},
                annotations=[{"text": "No data", "showarrow": False, "font": {"size": 14}}], template="plotly_white")
        
        name = df_country["Country"].iloc[0] if not df_country.empty else selected_iso
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(x=df_country["Value"], y=df_country["Life_Expectancy"], mode="lines+markers",
            marker=dict(size=6, color=df_country["Year"], colorscale="Viridis", showscale=False),
            line=dict(color="#2c3e50", width=1.5), text=df_country["Year"],
            hovertemplate="<b>%{text}</b><br>CO2 pc: %{x:.2f}t<br>Life: %{y:.1f} years<extra></extra>"))
        
        if len(df_country) > 0:
            fig.add_annotation(x=np.log10(df_country["Value"].iloc[0]), y=df_country["Life_Expectancy"].iloc[0],
                text=str(int(df_country["Year"].iloc[0])), showarrow=True, arrowhead=1, ax=20, ay=20, bgcolor="white")
            fig.add_annotation(x=np.log10(df_country["Value"].iloc[-1]), y=df_country["Life_Expectancy"].iloc[-1],
                text=str(int(df_country["Year"].iloc[-1])), showarrow=True, arrowhead=1, ax=-20, ay=-20, 
                bgcolor="white", font=dict(weight="bold"))
        
        fig.update_layout(title=f"{name}", template="plotly_white", margin={"r": 10, "t": 30, "l": 10, "b": 10},
            xaxis=dict(title="CO2 per capita (t)", type="log"), yaxis=dict(title="Life Expectancy (years)"), height=250)
        return fig
    
    df = _get_merged_data()
    df_country = df[df["ISOcode"] == selected_iso].sort_values("Year")
    name = df_country["Country"].iloc[0] if not df_country.empty else selected_iso
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df_country["GDP_pc"], y=df_country["CO2_pc"], mode="lines+markers",
        marker=dict(size=6, color=df_country["Year"], colorscale="Viridis", showscale=False),
        line=dict(color="#2c3e50", width=1.5), text=df_country["Year"],
        hovertemplate="<b>%{text}</b><br>GDP: $%{x:,.0f}<br>CO2: %{y:.2f}t<extra></extra>"))

    if not df_country.empty:
        fig.add_annotation(x=np.log10(df_country["GDP_pc"].iloc[0]), y=np.log10(df_country["CO2_pc"].iloc[0]),
            text=str(df_country["Year"].iloc[0]), showarrow=True, arrowhead=1, ax=20, ay=20, bgcolor="white")
        fig.add_annotation(x=np.log10(df_country["GDP_pc"].iloc[-1]), y=np.log10(df_country["CO2_pc"].iloc[-1]),
            text=str(df_country["Year"].iloc[-1]), showarrow=True, arrowhead=1, ax=-20, ay=-20, 
            bgcolor="white", font=dict(weight="bold"))

    fig.update_layout(title=f"{name}", template="plotly_white", margin={"r": 10, "t": 30, "l": 10, "b": 10},
        xaxis=dict(title="GDP pc ($)", type="log"), yaxis=dict(title="CO2 pc (t)", type="log"), height=250)
    return fig
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
    
    if view_mode == "life":
        return create_life_progress_analysis(selected_year)
    return create_decoupling_analysis(selected_year)


def create_decoupling_analysis(selected_year):
    """GDP decoupling analysis"""
    modal_title = "Decoupling: Breaking the Link"
    modal_subtitle = "Green vs Dirty Growth"
    modal_description = "Do we break the link between money and emissions? Compare % GDP growth (Horz.) vs % emissions growth (Vert.). Goal: 'Green Growth' zone (Bottom-Right): absolute decoupling."

    s_year = 1970
    
    if selected_year <= s_year:
        return create_baseline_figure(s_year, "Base year. Slide to analyze."), modal_title, modal_subtitle, modal_description, None
    
    s_c_start = aggregate_by_year(df_totals, s_year, "Value", strip_iso=False)
    s_c_end = aggregate_by_year(df_totals, selected_year, "Value", strip_iso=False)
    s_g_start = aggregate_by_year(df_gdp_total, s_year, "Value", strip_iso=False)
    s_g_end = aggregate_by_year(df_gdp_total, selected_year, "Value", strip_iso=False)

    df_delta = pd.concat([s_c_start, s_c_end, s_g_start, s_g_end], axis=1, 
                         keys=["CO2_s", "CO2_e", "GDP_s", "GDP_e"]).dropna()

    if df_delta.empty:
        return go.Figure().update_layout(title="No data"), modal_title, modal_subtitle, modal_description, None

    df_delta = df_delta[(df_delta["CO2_s"] != 0) & (df_delta["GDP_s"] != 0)]
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100
    df_delta["dGDP"] = ((df_delta["GDP_e"] / df_delta["GDP_s"]) - 1) * 100
    df_delta = map_countries_regions(df_delta, df_totals)
    df_delta = df_delta[(df_delta["dGDP"] < 400) & (df_delta["dGDP"] > -80) & (df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]

    fig = px.scatter(df_delta, x="dGDP", y="dCO2", color="Region", hover_name="Country",
                     title=f"Decoupling: {s_year} vs {selected_year}", template="plotly_white", height=450)
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    add_quadrant_zones(fig, [{"x0": 0, "x1": 400, "y0": -100, "y1": 0, "color": "green",
        "label": "GREEN GROWTH", "label_x": 50, "label_y": -20, "label_size": 14},
    {"x0": 0, "x1": 400, "y0": 0, "y1": 400, "color": "orange"}])
    fig.update_xaxes(title="GDP change (%)")
    fig.update_yaxes(title="CO2 emissions change (%)")
    return fig, modal_title, modal_subtitle, modal_description, None


def create_life_progress_analysis(selected_year):
    """Health progress analysis"""
    modal_title = "Health Progress: Life vs Emissions"
    modal_subtitle = "Sustainable Health Improvement"
    modal_description = "Do countries improve health while managing emissions? Compare change in life expectancy (Horz.) vs change in CO2 per capita (Vert.). Goal: 'Sustainable Progress' zone (Top-Right)."
    s_year = 1970
    
    if selected_year <= s_year:
        return create_baseline_figure(s_year, "Base year. Slide to analyze."), modal_title, modal_subtitle, modal_description, None
    
    s_l_start = aggregate_by_year(df_life_expectancy, s_year, "Life_Expectancy", strip_iso=True)
    s_l_end = aggregate_by_year(df_life_expectancy, selected_year, "Life_Expectancy", strip_iso=True)
    s_c_start = aggregate_by_year(df_capita, s_year, "Value", strip_iso=False)
    s_c_end = aggregate_by_year(df_capita, selected_year, "Value", strip_iso=False)
    
    df_delta = pd.concat([s_l_start, s_l_end, s_c_start, s_c_end], axis=1, keys=["Life_s", "Life_e", "CO2_s", "CO2_e"]).dropna()
    
    if df_delta.empty:
        return go.Figure().update_layout(title="No data"), modal_title, modal_subtitle, modal_description, None
    
    df_delta["dLife"] = df_delta["Life_e"] - df_delta["Life_s"]
    df_delta = df_delta[df_delta["CO2_s"] != 0]
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100
    df_delta = map_countries_regions(df_delta, df_capita)
    df_delta = df_delta[(df_delta["dLife"] > -20) & (df_delta["dLife"] < 40) & (df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]
    
    fig = px.scatter(df_delta, x="dLife", y="dCO2", color="Region", hover_name="Country",
                     title=f"Health Progress: {s_year} vs {selected_year}", template="plotly_white", height=450)
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    add_quadrant_zones(fig, [{"x0": 0, "x1": 40, "y0": -100, "y1": 0, "color": "green",
        "label": "SUSTAINABLE PROGRESS", "label_x": 15, "label_y": -30, "label_size": 12},
       {"x0": 0, "x1": 40, "y0": 0, "y1": 400, "color": "orange", 
        "label": "HIGH COST", "label_x": 15, "label_y": 100, "label_size": 11}])
    fig.update_xaxes(title="Change in Life Expectancy (years)")
    fig.update_yaxes(title="Change in CO2 per Capita (%)")
    
    df_delta["Sustainability_Score"] = df_delta["dLife"] - (df_delta["dCO2"] / 10)
    top_sustainable = df_delta.nlargest(5, "Sustainability_Score")[["Country", "dLife", "dCO2", "Sustainability_Score"]]
    least_sustainable = df_delta.nsmallest(5, "Sustainability_Score")[["Country", "dLife", "dCO2", "Sustainability_Score"]]
    
    def format_life_metrics(row):
        return [f"Life: +{row['dLife']:.1f} years | ",
            html.Span(f"CO2: {row['dCO2']:.0f}%", className="text-success" if row['dCO2'] < 0 else "text-warning")]
    
    top_section = create_ranking_html(top_sustainable, least_sustainable, 
                                       "SUSTAINABLE PROGRESS", "HIGH COST", format_life_metrics)
    return fig, modal_title, modal_subtitle, modal_description, top_section
@callback(
    Output("corr-selected-iso-store", "data"),
    Input("corr-bubble-graph", "clickData"),
    prevent_initial_call=False
)
def update_corr_country_store(clickData):
    """Update country selection on bubble click"""
    if clickData and clickData.get("points"):
        try:
            return clickData["points"][0]["customdata"][0]
        except:
            return None
    return None