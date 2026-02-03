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
        
        # GDP Stats cards
        dbc.Row(id="gdp-stats-container", className="mb-3 g-2"),

        # Controls for GDP view
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Label("View Mode:", className="fw-bold mb-1 small"),
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
            ]), className="shadow-sm"), width=8),

            dbc.Col(
                dbc.Button("Advanced Prosperity Analysis", id="open-advanced-gdp",
                           color="primary", className="w-100 shadow-sm h-100", size="sm"),
                width=4
            ),
        ], className="mb-3"),

        # Map and Country Evolution
        dbc.Row([
            dbc.Col(dcc.Graph(id="gdp-map"), width=12)
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(dcc.Graph(id="gdp-country-lines"), width=12)
        ]),

        # Modal for Advanced Analysis
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Advanced Economic Analysis")),
                dbc.ModalBody([
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
    return df_gdp_total if view == "total" else df_gdp_capita

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

    # Use log scale for better visualization of discrepancies
    dff["ColorValue"] = np.log10(dff["Value"])

    fig = px.choropleth(
        dff,
        locations="ISOcode",
        color="ColorValue",
        hover_name="Country",
        hover_data={"Value": ":,.2f", "ColorValue": False},
        color_continuous_scale="Viridis",
        height=400
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        coloraxis_colorbar=dict(title="log10(GDP)", thickness=15, len=0.8)
    )
    return fig

@callback(
    Output("gdp-country-lines", "figure"),
    Input("gdp-map", "clickData"),
    Input("year-slider", "value"),
    Input('tabs', 'active_tab')
)
def update_country_lines(clickData, selected_year, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return go.Figure()

    iso = None
    if clickData and clickData.get("points"):
        iso = clickData["points"][0].get("location")

    # Default: country with highest total GDP in that year if none clicked
    dff_y = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    if iso is None and not dff_y.empty:
        iso = dff_y.loc[dff_y["Value"].idxmax(), "ISOcode"]

    if iso is None:
        return go.Figure().update_layout(title="Click on a country to see its evolution")

    c_total = df_gdp_total[df_gdp_total["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    c_cap = df_gdp_capita[df_gdp_capita["ISOcode"] == iso].dropna(subset=["Value"]).copy()

    c_total = c_total[c_total["Year"] <= selected_year]
    c_cap = c_cap[c_cap["Year"] <= selected_year]

    if c_total.empty and c_cap.empty:
        return go.Figure().update_layout(title="No historical data for this country")

    name = c_total["Country"].iloc[0] if not c_total.empty else c_cap["Country"].iloc[0]

    avg_total = df_gdp_total.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_cap = df_gdp_capita.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_total = avg_total[avg_total["Year"] <= selected_year]
    avg_cap = avg_cap[avg_cap["Year"] <= selected_year]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Total GDP (M$)", "GDP per Capita ($)"),
                        vertical_spacing=0.15)

    fig.add_trace(go.Scatter(x=c_total["Year"], y=c_total["Value"], mode="lines", name=f"{name} (Total)"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=avg_total["Year"], y=avg_total["Value"], mode="lines",
                             name="Global Avg (Total)", line=dict(color="gray", dash="dash")),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=c_cap["Year"], y=c_cap["Value"], mode="lines", name=f"{name} (Per Capita)"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=avg_cap["Year"], y=avg_cap["Value"], mode="lines",
                             name="Global Avg (Per Cap)", line=dict(color="gray", dash="dash")),
                  row=2, col=1)

    fig.update_layout(
        height=450,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig

@callback(
    Output("modal-advanced-gdp", "is_open"),
    [Input("open-advanced-gdp", "n_clicks"), Input("close-advanced-gdp", "n_clicks")],
    [State("modal-advanced-gdp", "is_open")]
)
def toggle_modal_gdp(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("modal-advanced-body-gdp", "children"),
    Input("year-slider", "value"),
    Input('tabs', 'active_tab')
)
def update_advanced_modal_gdp(selected_year, active_tab):
    if active_tab != 'tab-2' or selected_year is None:
        return None

    # Top 10 total
    d1 = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    top_total = d1.nlargest(10, "Value").sort_values("Value")
    fig1 = px.bar(top_total, x="Value", y="Country", orientation="h",
                  title=f"Top 10 Total GDP ({selected_year})", template="plotly_white")

    # Top 10 per capita
    d2 = df_gdp_capita[df_gdp_capita["Year"] == selected_year].dropna(subset=["Value"])
    top_cap = d2.nlargest(10, "Value").sort_values("Value")
    fig2 = px.bar(top_cap, x="Value", y="Country", orientation="h",
                  title=f"Top 10 GDP per Capita ({selected_year})", template="plotly_white")

    # Volatility and biggest change
    hist = df_gdp_total[df_gdp_total["Year"] <= selected_year].dropna(subset=["Value"]).copy()
    hist = hist[hist["Value"] > 0].sort_values(["ISOcode", "Year"])
    hist["pct_yoy"] = hist.groupby("ISOcode")["Value"].pct_change() * 100

    name_map = hist.groupby("ISOcode")["Country"].first().to_dict()

    vol = hist.groupby("ISOcode")["pct_yoy"].std().dropna().sort_values(ascending=False).head(10)
    vol_df = vol.reset_index().rename(columns={"pct_yoy": "Std_%YoY"})
    vol_df["Country"] = vol_df["ISOcode"].map(name_map)
    fig3 = px.bar(vol_df.sort_values("Std_%YoY"), x="Std_%YoY", y="Country", orientation="h",
                  title="GDP Volatility (std %YoY)", template="plotly_white")

    big = hist.groupby("ISOcode")["pct_yoy"].apply(lambda s: np.nanmax(np.abs(s.values)) if not s.dropna().empty else np.nan).dropna().sort_values(ascending=False).head(10)
    big_df = big.reset_index().rename(columns={"pct_yoy": "Max_|%YoY|"})
    big_df["Country"] = big_df["ISOcode"].map(name_map)
    fig4 = px.bar(big_df.sort_values("Max_|%YoY|"), x="Max_|%YoY|", y="Country", orientation="h",
                  title="Biggest Annual Change (%YoY)", template="plotly_white")

    for f in [fig1, fig2, fig3, fig4]:
        f.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), width=6),
            dbc.Col(dcc.Graph(figure=fig2), width=6),
        ], className="g-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig3), width=6),
            dbc.Col(dcc.Graph(figure=fig4), width=6),
        ], className="g-2"),
    ])
