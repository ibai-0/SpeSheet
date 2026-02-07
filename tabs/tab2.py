from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from prepare_data import (
    df_gdp_total,
    df_gdp_capita,
    df_life_expectancy,
    ISO_TO_REGION,
    TAB2_GDP_TOTAL_AVG_BY_YEAR,
    TAB2_GDP_CAPITA_AVG_BY_YEAR,
    TAB2_LIFE_AVG_BY_YEAR,
    TAB2_LIFE_CONTINENT_AVG,
    TAB2_LIFE_CONTINENT_COLOR_MAP,
    tab2_get_gdp_year_df,
    tab2_get_gdp_map_df,
    tab2_get_life_year_df,
    tab2_get_default_iso_gdp,
    tab2_get_default_iso_life,
    tab2_get_gdp_country_series,
    tab2_get_life_country_series,
)
from components import controls


# =============================================================================
# Small UI helpers (to keep callbacks compact)
# =============================================================================

_MAP_ANNOTATION = [dict(
    x=0.5, y=-0.1, xref="paper", yref="paper",
    text="Interactive: Select a country to see details >",
    showarrow=False, font=dict(size=12, color="gray")
)]

_COMMON_GEO = dict(showframe=False, showcoastlines=True, projection_type="equirectangular")
_COMMON_MAP_MARGIN = dict(l=0, r=0, t=0, b=0)


def _empty_fig(title=None) -> go.Figure:
    """Return a minimal placeholder figure."""
    fig = go.Figure()
    if title:
        fig.update_layout(title=title)
    return fig


def _pair(fig: go.Figure):
    """Tab 2 duplicates the same figure into two containers (GDP/Life)."""
    return fig, fig


def _clicked_iso(click_data):
    """Extract ISO code from choropleth clickData."""
    if click_data and click_data.get("points"):
        return click_data["points"][0].get("location")
    return None


def _style_choropleth(fig: go.Figure, colorbar_title: str) -> go.Figure:
    """Apply the shared map styling used in Tab 2."""
    fig.update_layout(
        margin=_COMMON_MAP_MARGIN,
        coloraxis_colorbar=dict(title=colorbar_title, thickness=15, len=0.6),
        geo=_COMMON_GEO,
        annotations=_MAP_ANNOTATION,
    )
    return fig


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
                dbc.Button(
                    id="advanced-button-text",
                    children="Advanced Prosperity Analysis",
                    color="primary",
                    className="w-100 shadow-sm h-100",
                    size="sm"
                ),
                width=4
            ),
        ], className="mb-2"),

        # --- GDP VIEW LAYOUT: MAP LEFT, LINES RIGHT ---
        html.Div(id="gdp-layout-container", children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-map-title-gdp", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-map-description-gdp", className="text-muted small mb-2"),
                        dcc.Graph(id="gdp-map")
                    ]), className="shadow-sm h-100")
                ], width=8),

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
            dbc.Row([
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-map-title-life", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-map-description-life", className="text-muted small mb-2"),
                        dcc.Graph(id="gdp-map-life")
                    ]), className="shadow-sm")
                ], width=12)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Card(dbc.CardBody([
                        html.H5(id="tab2-lines-title-life", className="text-primary fw-bold mb-1"),
                        html.P(id="tab2-lines-description-life", className="text-muted small mb-2"),
                        dcc.Graph(id="gdp-country-lines-life")
                    ], className="py-2 px-2"), className="shadow-sm")
                ], width=6),

                dbc.Col([html.Div(id="tab2-continental-chart-container")], width=6)
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


# =============================================================================
# Callbacks
# =============================================================================

@callback(
    [Output("tab2-view-mode-store", "data"),
     Output("btn-tab2-view-gdp", "color"),
     Output("btn-tab2-view-life", "color")],
    [Input("btn-tab2-view-gdp", "n_clicks"),
     Input("btn-tab2-view-life", "n_clicks")],
    prevent_initial_call=False
)
def toggle_tab2_view_mode(n_gdp, n_life):
    """Toggle between GDP and Life Expectancy views."""
    if (ctx.triggered_id if ctx.triggered else None) == "btn-tab2-view-life":
        return "life", "outline-primary", "primary"
    return "gdp", "primary", "outline-primary"


@callback(
    Output("gdp-controls-row", "style"),
    Input("tab2-view-mode-store", "data")
)
def toggle_gdp_controls_visibility(view_mode):
    """Hide the GDP controls when the Life Expectancy view is active."""
    return {"display": "none"} if view_mode == "life" else {}


@callback(
    [Output("gdp-layout-container", "style"),
     Output("life-layout-container", "style")],
    Input("tab2-view-mode-store", "data")
)
def toggle_layout_visibility(view_mode):
    """Show/hide the layout containers based on the selected view."""
    return ({"display": "none"}, {}) if view_mode == "life" else ({}, {"display": "none"})


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
    """Update titles and descriptions based on view mode (text must stay identical)."""
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
        gdp_map_title = gdp_map_desc = gdp_lines_title = gdp_lines_desc = ""
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
        modal_intro = ""
        button_text = "Advanced Prosperity Analysis"

        # Life layout gets empty values (not visible)
        map_title = map_desc = lines_title = lines_desc = ""

    return (
        gdp_map_title, gdp_map_desc, gdp_lines_title, gdp_lines_desc,
        map_title, map_desc, lines_title, lines_desc,
        modal_title, modal_intro, button_text
    )


@callback(
    Output("gdp-stats-container", "children"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input("tabs", "active_tab"),
    Input("tab2-view-mode-store", "data")
)
def update_gdp_cards(selected_year, view, active_tab, view_mode):
    """Update the summary cards at the top of Tab 2."""
    if active_tab != "tab-2" or selected_year is None:
        return []

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        dff = tab2_get_life_year_df(selected_year, filter_small_isos=True)
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
    dff = tab2_get_gdp_year_df(selected_year, view)
    if dff.empty:
        return dbc.Col(dbc.Alert("No data available for this year.", color="warning"), width=12)

    max_row = dff.loc[dff["Value"].idxmax()]
    mean_val = float(dff["Value"].mean())

    if view == "total":
        global_val = float(dff["Value"].sum())
        left_title, left_value = "Global GDP (Sum)", f"{global_val:,.0f} M$"
        right_title, right_value = "National Average", f"{mean_val:,.0f} M$"
    else:
        left_title, left_value = "Avg GDP per Capita", f"{mean_val:,.0f} $"
        right_title, right_value = "Median GDP per Capita", f"{float(dff['Value'].median()):,.0f} $"

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


@callback(
    [Output("gdp-map", "figure"),
     Output("gdp-map-life", "figure")],
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
    Input("tabs", "active_tab"),
    Input("tab2-view-mode-store", "data")
)
def update_gdp_map(selected_year, view, active_tab, view_mode):
    """Update the choropleth map for GDP or Life Expectancy."""
    if active_tab != "tab-2" or selected_year is None:
        return _pair(_empty_fig())

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        dff = tab2_get_life_year_df(selected_year, filter_small_isos=True)
        if dff.empty:
            return _pair(_empty_fig("No data to show"))

        fig = px.choropleth(
            dff,
            locations="ISOcode",
            color="Life_Expectancy",
            hover_name="Country",
            hover_data={"Life_Expectancy": ":.1f", "ISOcode": False},
            color_continuous_scale="RdYlGn",
            height=400
        )
        _style_choropleth(fig, "Age")
        return _pair(fig)

    # --- GDP VIEW (ORIGINAL) ---
    dff = tab2_get_gdp_map_df(selected_year, view)
    if dff.empty:
        return _pair(_empty_fig("No data to show"))

    fig = px.choropleth(
        dff,
        locations="ISOcode",
        color="ColorValue",
        hover_name="Country",
        hover_data={"Value": ":,.2f", "ColorValue": False},
        color_continuous_scale="Viridis",
        height=550
    )
    _style_choropleth(fig, "log10(GDP)")
    return _pair(fig)


@callback(
    [Output("gdp-country-lines", "figure"),
     Output("gdp-country-lines-life", "figure")],
    [Input("gdp-map", "clickData"),
     Input("gdp-map-life", "clickData")],
    Input("year-slider", "value"),
    Input("tabs", "active_tab"),
    Input("tab2-view-mode-store", "data")
)
def update_country_lines(clickData_gdp, clickData_life, selected_year, active_tab, view_mode):
    """Update the right-side historical lines based on the selected country."""
    if active_tab != "tab-2" or selected_year is None:
        return _pair(_empty_fig())

    click_data = clickData_life if view_mode == "life" else clickData_gdp
    iso = _clicked_iso(click_data)

    # Fallback selection (same logic as before)
    if iso is None:
        iso = tab2_get_default_iso_life(selected_year) if view_mode == "life" else tab2_get_default_iso_gdp(selected_year)

    if iso is None:
        return _pair(_empty_fig("Click on a country"))

    # --- LIFE EXPECTANCY VIEW ---
    if view_mode == "life":
        c_life = tab2_get_life_country_series(iso)
        if c_life.empty:
            return _pair(_empty_fig("No data for selected country"))

        name = c_life["Country"].iloc[0]
        avg_life = TAB2_LIFE_AVG_BY_YEAR

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=c_life["Year"],
            y=c_life["Life_Expectancy"],
            mode="lines",
            name=f"{name}",
            line=dict(width=3, color="#2ecc71")
        ))
        fig.add_trace(go.Scatter(
            x=avg_life["Year"],
            y=avg_life["Life_Expectancy"],
            mode="lines",
            name="Global Average",
            line=dict(color="gray", dash="dash", width=2)
        ))

        fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")
        fig.update_traces(hovertemplate="%{fullData.name}<br>Year: %{x}<br>Life Exp: %{y:.1f} years<extra></extra>")
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
        return _pair(fig)

    # --- GDP VIEW (ORIGINAL) ---
    c_total, c_cap, name = tab2_get_gdp_country_series(iso)
    if name is None:
        return _pair(_empty_fig("No data for selected country"))

    avg_total = TAB2_GDP_TOTAL_AVG_BY_YEAR
    avg_cap = TAB2_GDP_CAPITA_AVG_BY_YEAR

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=(f"Total GDP ({name})", f"GDP per Capita ({name})"),
        vertical_spacing=0.15
    )

    fig.add_trace(go.Scatter(
        x=c_total["Year"], y=c_total["Value"], mode="lines", name=f"{name} (Total)",
        line=dict(width=3), hovertemplate="Year: %{x}<br>GDP: $%{y:,.0f}M<extra></extra>"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=avg_total["Year"], y=avg_total["Value"], mode="lines", name="Global Avg",
        line=dict(color="gray", dash="dash"),
        hovertemplate="Year: %{x}<br>Avg: $%{y:,.0f}M<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=c_cap["Year"], y=c_cap["Value"], mode="lines", name=f"{name} (Per Capita)",
        line=dict(width=3), showlegend=True,
        hovertemplate="Year: %{x}<br>GDP pc: $%{y:,.0f}<extra></extra>"
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=avg_cap["Year"], y=avg_cap["Value"], mode="lines", name="Global Avg",
        line=dict(color="gray", dash="dash"), showlegend=False,
        hovertemplate="Year: %{x}<br>Avg: $%{y:,.0f}<extra></extra>"
    ), row=2, col=1)

    fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")
    fig.update_layout(
        height=550,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified"
    )
    return _pair(fig)


@callback(
    Output("tab2-continental-chart-container", "children"),
    Input("year-slider", "value"),
    Input("tabs", "active_tab"),
    Input("tab2-view-mode-store", "data")
)
def update_continental_progress(selected_year, active_tab, view_mode):
    """Show the continental life expectancy progress chart (life view only)."""
    if active_tab != "tab-2" or view_mode != "life" or selected_year is None:
        return None

    continent_avg = TAB2_LIFE_CONTINENT_AVG

    fig = px.line(
        continent_avg,
        x="Year",
        y="Life_Expectancy",
        color="Continent",
        template="plotly_white",
        markers=True,
        color_discrete_map=TAB2_LIFE_CONTINENT_COLOR_MAP
    )

    fig.add_vline(x=selected_year, line_width=1, line_dash="dot", line_color="red")
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Life Exp: %{y:.1f} years<extra></extra>")
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
        html.P("Average life expectancy evolution by continent over time.", className="text-muted small mb-2"),
        dcc.Graph(figure=fig)
    ], className="py-2 px-2"), className="shadow-sm")


@callback(
    Output("modal-advanced-gdp", "is_open"),
    [Input("advanced-button-text", "n_clicks"), Input("close-advanced-gdp", "n_clicks")],
    [State("modal-advanced-gdp", "is_open")]
)
def toggle_modal_gdp(n1, n2, is_open):
    """Open/close the advanced modal."""
    if n1 or n2:
        return not is_open
    return is_open


@callback(
    Output("modal-advanced-body-gdp", "children"),
    Input("year-slider", "value"),
    Input("tabs", "active_tab"),
    Input("tab2-view-mode-store", "data")
)
def update_advanced_modal_gdp(selected_year, active_tab, view_mode):
    """Update the advanced analysis modal content."""
    if active_tab != "tab-2" or selected_year is None:
        return None

    if view_mode == "life":
        return create_life_expectancy_advanced_analysis(selected_year)

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