from dash import html, dcc, dash_table, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from prepare_data import df_totals, df_capita, df_sectors, df_correlation, df_cumulative, df_gdp_capita, df_gdp_total
import numpy as np
from dash import State
from plotly.subplots import make_subplots

@callback(
    Output('stats-container', 'children'),
    Input('year-slider', 'value')
)
def update_stats(selected_year):
    """Genera las tarjetas de métricas globales del banner superior."""
    dff = df_totals[df_totals['Year'] == selected_year]
    global_sum = dff['Value'].sum()
    max_row = dff.loc[dff['Value'].idxmax()]
    
    return [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Emisiones Globales", className="card-subtitle text-muted"),
            html.H4(f"{global_sum:,.1f} Mt CO2", className="text-primary")
        ]), className="border-start border-primary border-4")),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Máximo Emisor", className="card-subtitle text-muted"),
            html.H4(f"{max_row['Country']}", className="text-danger")
        ]), className="border-start border-danger border-4")),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Promedio por Nación", className="card-subtitle text-muted"),
            html.H4(f"{dff['Value'].mean():,.2f} Mt", className="text-success")
        ]), className="border-start border-success border-4"))
    ]

@callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value')
)

def update_tab_content(active_tab, selected_year):
    return render_content(active_tab, selected_year)

def _get_gdp_df(view):
    return df_gdp_total if view == "total" else df_gdp_capita

@callback(
    Output("gdp-stats-container", "children"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
)
def update_gdp_cards(selected_year, view):
    dff = _get_gdp_df(view)
    dff = dff[dff["Year"] == selected_year].dropna(subset=["Value"])
    if dff.empty:
        return dbc.Col(dbc.Alert("No hay datos de PIB para este año.", color="warning"), width=12)

    max_row = dff.loc[dff["Value"].idxmax()]
    mean_val = float(dff["Value"].mean())

    if view == "total":
        global_val = float(dff["Value"].sum())
        left_title = "PIB Global (suma)"
        left_value = f"{global_val:,.0f}"
        right_title = "Promedio PIB por nación"
        right_value = f"{mean_val:,.0f}"
    else:
        # Per cápita: global “razonable” = media (por país)
        left_title = "PIB per cápita global (media países)"
        left_value = f"{mean_val:,.0f}"
        right_title = "Mediana PIB per cápita"
        right_value = f"{float(dff['Value'].median()):,.0f}"

    return [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6(left_title, className="card-subtitle text-muted"),
            html.H4(left_value, className="text-primary")
        ]), className="border-start border-primary border-4"), width=4),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("PIB Máximo", className="card-subtitle text-muted"),
            html.H4(f"{max_row['Country']}", className="text-danger")
        ]), className="border-start border-danger border-4"), width=4),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6(right_title, className="card-subtitle text-muted"),
            html.H4(right_value, className="text-success")
        ]), className="border-start border-success border-4"), width=4),
    ]


@callback(
    Output("gdp-map", "figure"),
    Input("year-slider", "value"),
    Input("gdp-view", "value"),
)
def update_gdp_map(selected_year, view):
    dff = _get_gdp_df(view)
    dff = dff[dff["Year"] == selected_year].dropna(subset=["Value"]).copy()
    dff = dff[dff["Value"] > 0]

    if dff.empty:
        return go.Figure().update_layout(title="No hay datos para mostrar")

    # log para que se vea bien en mapa
    dff["ColorValue"] = np.log10(dff["Value"])

    fig = px.choropleth(
        dff,
        locations="ISOcode",
        color="ColorValue",
        hover_name="Country",
        hover_data={"Value": True, "ColorValue": False},
        color_continuous_scale="Viridis",
        title=f"PIB ({'Total' if view=='total' else 'Per cápita'}) ({selected_year})"
    )
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    return fig


@callback(
    Output("gdp-country-lines", "figure"),
    Input("gdp-map", "clickData"),
    Input("year-slider", "value"),
)
def update_country_lines(clickData, selected_year):
    iso = None
    if clickData and clickData.get("points"):
        iso = clickData["points"][0].get("location")

    # default: país con mayor PIB total en ese año
    dff_y = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    if iso is None and not dff_y.empty:
        iso = dff_y.loc[dff_y["Value"].idxmax(), "ISOcode"]

    if iso is None:
        return go.Figure().update_layout(title="Haz click en un país del mapa para ver su evolución.")

    c_total = df_gdp_total[df_gdp_total["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    c_cap = df_gdp_capita[df_gdp_capita["ISOcode"] == iso].dropna(subset=["Value"]).copy()

    c_total = c_total[c_total["Year"] <= selected_year]
    c_cap = c_cap[c_cap["Year"] <= selected_year]

    name = (c_total["Country"].iloc[0] if not c_total.empty
            else (c_cap["Country"].iloc[0] if not c_cap.empty else iso))

    avg_total = df_gdp_total.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_cap = df_gdp_capita.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    avg_total = avg_total[avg_total["Year"] <= selected_year]
    avg_cap = avg_cap[avg_cap["Year"] <= selected_year]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("PIB total", "PIB per cápita"))

    fig.add_trace(go.Scatter(x=c_total["Year"], y=c_total["Value"], mode="lines", name=f"{name} (Total)"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=avg_total["Year"], y=avg_total["Value"], mode="lines",
                             name="Media global (Total)", line=dict(color="red", dash="dash")),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=c_cap["Year"], y=c_cap["Value"], mode="lines", name=f"{name} (Per cápita)"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=avg_cap["Year"], y=avg_cap["Value"], mode="lines",
                             name="Media global (Per cápita)", line=dict(color="red", dash="dash")),
                  row=2, col=1)

    fig.update_layout(
        title=f"Evolución PIB: {name} (hasta {selected_year})",
        template="plotly_white",
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=20, r=20, t=80, b=20),
    )
    return fig


@callback(
    Output("advanced-modal", "is_open"),
    Input("open-advanced", "n_clicks"),
    Input("close-advanced", "n_clicks"),
    State("advanced-modal", "is_open"),
)
def toggle_modal(open_n, close_n, is_open):
    if open_n or close_n:
        return not is_open
    return is_open


@callback(
    Output("adv-top10-total", "figure"),
    Output("adv-top10-capita", "figure"),
    Output("adv-volatility", "figure"),
    Output("adv-biggest-change", "figure"),
    Input("year-slider", "value"),
)
def advanced_figs(selected_year):
    # Top 10 total
    d1 = df_gdp_total[df_gdp_total["Year"] == selected_year].dropna(subset=["Value"])
    top_total = d1.nlargest(10, "Value").sort_values("Value")
    fig1 = px.bar(top_total, x="Value", y="Country", orientation="h",
                  title=f"Top 10 PIB total ({selected_year})")

    # Top 10 per cápita
    d2 = df_gdp_capita[df_gdp_capita["Year"] == selected_year].dropna(subset=["Value"])
    top_cap = d2.nlargest(10, "Value").sort_values("Value")
    fig2 = px.bar(top_cap, x="Value", y="Country", orientation="h",
                  title=f"Top 10 PIB per cápita ({selected_year})")

    # Volatilidad y mayor cambio (PIB total)
    hist = df_gdp_total[df_gdp_total["Year"] <= selected_year].dropna(subset=["Value"]).copy()
    hist = hist[hist["Value"] > 0].sort_values(["ISOcode", "Year"])
    hist["pct_yoy"] = hist.groupby("ISOcode")["Value"].pct_change() * 100

    name_map = hist.groupby("ISOcode")["Country"].first().to_dict()

    vol = hist.groupby("ISOcode")["pct_yoy"].std().dropna().sort_values(ascending=False).head(15)
    vol_df = vol.reset_index().rename(columns={"pct_yoy": "Std_%YoY"})
    vol_df["Country"] = vol_df["ISOcode"].map(name_map)
    fig3 = px.bar(vol_df.sort_values("Std_%YoY"), x="Std_%YoY", y="Country", orientation="h",
                  title=f"Volatilidad PIB total (std %YoY) hasta {selected_year}")

    big = hist.groupby("ISOcode")["pct_yoy"].apply(lambda s: np.nanmax(np.abs(s.values))).dropna().sort_values(ascending=False).head(15)
    big_df = big.reset_index().rename(columns={"pct_yoy": "Max_|%YoY|"})
    big_df["Country"] = big_df["ISOcode"].map(name_map)
    fig4 = px.bar(big_df.sort_values("Max_|%YoY|"), x="Max_|%YoY|", y="Country", orientation="h",
                  title=f"Mayor cambio anual (max |%YoY|) hasta {selected_year}")

    return fig1, fig2, fig3, fig4

def render_content(tab, selected_year):
    if tab == 'tab-1':
        # 1. Mapa mundi con df_totals + visualización del max_emitter
        dff = df_totals[df_totals['Year'] == selected_year]
        fig = px.choropleth(
            dff, locations="ISOcode", color="Value", hover_name="Country",
            color_continuous_scale="Viridis", title=f"Distribución de Emisiones Totales ({selected_year})"
        )
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=12)
        ])

    elif tab == 'tab-2':
        # 2. Sectores (Sunburst) + Tendencia acumulada
        dff_s = df_sectors[df_sectors['Year'] == selected_year]
        fig_sun = px.sunburst(
            dff_s, path=['Country', 'Sector'], values='Value',
            title=f"Desglose Sectorial por País ({selected_year})"
        )
        
        # Gráfico de línea para ver el cambio acumulado histórico
        fig_trend = px.line(
            df_cumulative, x="Year", y="Cumulative_Value", color="Country",
            title="Evolución Histórica Acumulada (Top 10)",
            # Filtramos solo los 10 países con más emisiones históricas para no saturar
            range_x=[1970, selected_year]
        )
        
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_sun), width=6),
            dbc.Col(dcc.Graph(figure=fig_trend), width=6)
        ])

    elif tab == 'tab-3':
        # 3. Ranking per capita + Correlación
        dff_c = df_capita[df_capita['Year'] == selected_year].sort_values('Value', ascending=False).head(15)
        fig_rank = px.bar(
            dff_c, x='Value', y='Country', orientation='h',
            title="Top 15: Emisiones por Persona", color='Value'
        )
        
        # Gráfico de correlación entre Total y Per Capita
        dff_corr = df_correlation[df_correlation['Year'] == selected_year]
        fig_corr = px.scatter(
            dff_corr, x="Total_Emissions", y="Per_Capita", 
            hover_name="Country", log_x=True, trendline="ols",
            title="Correlación: Emisiones Totales vs Per Capita (Escala Log)"
        )
        
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_rank), width=6),
            dbc.Col(dcc.Graph(figure=fig_corr), width=6)
        ])

    elif tab == 'tab-4':
        # 4. Explorador de datos crudos
        dff = df_totals[df_totals['Year'] == selected_year]
        return html.Div([
            dash_table.DataTable(
                data=dff.to_dict('records'),
                columns=[{"name": i, "id": i} for i in dff.columns],
                sort_action="native", filter_action="native",
                page_size=10,
                style_header={'backgroundColor': '#2c3e50', 'color': 'white'},
                style_cell={'textAlign': 'left'}
            )
        ], className="p-4")
    elif tab == 'tab-5':
        return html.Div([
            # KPI cards
            dbc.Row(id="gdp-stats-container", className="mb-3"),

            # Controls
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Div("Vista:", className="fw-bold mb-2"),
                    dbc.RadioItems(
                        id="gdp-view",
                        options=[
                            {"label": "PIB total", "value": "total"},
                            {"label": "PIB per cápita", "value": "capita"},
                        ],
                        value="total",
                        inline=True
                    ),
                ]), className="shadow-sm"), width=8),

                dbc.Col(
                    dbc.Button("Advanced Analysis", id="open-advanced",
                               color="primary", className="w-100 shadow-sm"),
                    width=4
                ),
            ], className="mb-3"),

            # Map
            dbc.Row([
                dbc.Col(dcc.Graph(id="gdp-map"), width=12)
            ], className="mb-3"),

            # Country lines (click)
            dbc.Row([
                dbc.Col(dcc.Graph(id="gdp-country-lines"), width=12)
            ]),

            # Modal
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Advanced Analysis")),
                    dbc.ModalBody([
                        dbc.Row([
                            dbc.Col(dcc.Graph(id="adv-top10-total"), width=6),
                            dbc.Col(dcc.Graph(id="adv-top10-capita"), width=6),
                        ]),
                        dbc.Row([
                            dbc.Col(dcc.Graph(id="adv-volatility"), width=6),
                            dbc.Col(dcc.Graph(id="adv-biggest-change"), width=6),
                        ]),
                    ]),
                    dbc.ModalFooter(dbc.Button("Close", id="close-advanced", className="ms-auto")),
                ],
                id="advanced-modal",
                is_open=False,
                size="xl",
                scrollable=True,
            ),
        ])