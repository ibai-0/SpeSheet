from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from prepare_data import df_gdp_total, df_gdp_capita, df_life_expectancy, ISO_TO_REGION
from components import controls

def _get_gdp_df(view):
    return df_gdp_total if view == 'total' else df_gdp_capita

def layout():
    return html.Div(className='tab-animacion', children=[
        controls.layout(),
        dbc.Row([dbc.Col([dbc.ButtonGroup([
            dbc.Button("GDP", id="btn-tab2-view-gdp", color="primary", size="lg", className="px-5"),
            dbc.Button("Life Expectancy", id="btn-tab2-view-life", color="outline-primary", size="lg", className="px-5")
        ], className="mb-3 d-flex justify-content-center w-100")], width=12)], className="mb-3"),
        dcc.Store(id="tab2-view-mode-store", data="gdp"),
        dbc.Row(id="gdp-stats-container", className="mb-3 g-2"),
        dbc.Row(id="gdp-controls-row", children=[
            dbc.Col(dbc.Card(dbc.CardBody([html.Div([
                html.Label("View Mode:", className="fw-bold me-4 mb-0 small"),
                dbc.RadioItems(id="gdp-view", options=[{"label": "Total GDP", "value": "total"}, {"label": "GDP per Capita", "value": "capita"}], value="total", inline=True, className="small")
            ], className="d-flex align-items-center")], className="py-2 px-3"), className="shadow-sm"), width=8),
            dbc.Col(dbc.Button(id="advanced-button-text", children="Advanced Prosperity Analysis", color="primary", className="w-100 shadow-sm h-100", size="sm"), width=4),
        ], className="mb-2"),
        html.Div(id="gdp-layout-container", children=[dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5(id="tab2-map-title-gdp", className="text-primary fw-bold mb-1"),
                    html.P(id="tab2-map-description-gdp", className="text-muted small mb-2"),
                    dcc.Graph(id="gdp-map")
                ]), className="shadow-sm h-100")
            ], width=8),
            dbc.Col([
                dbc.Alert([
                    html.I(className="bi bi-pin-map-fill me-2"),
                    html.Span("Selected country: "),
                    html.Strong(id="selected-country-display", children="Click on the map")
                ], color="info", className="py-2 px-3 mb-3 d-flex align-items-center", style={"fontSize": "0.9rem"}),
                dbc.Card(dbc.CardBody([
                    html.H5("GDP Total", className="text-primary fw-bold mb-1"),
                    html.P("History of the selected country", className="text-muted small mb-2"),
                    dcc.Graph(id="gdp-country-total")
                ], className="py-2 px-2"), className="shadow-sm mb-3"),
                dbc.Card(dbc.CardBody([
                    html.H5("GDP per Capita", className="text-primary fw-bold mb-1"),
                    html.P("History of the selected country", className="text-muted small mb-2"),
                    dcc.Graph(id="gdp-country-capita")
                ], className="py-2 px-2"), className="shadow-sm")
            ], width=4)
        ], className="mb-3 g-3")]),
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
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Advanced Prosperity Analysis")),
            dbc.ModalBody(id="modal-advanced-body-gdp"),
            dbc.ModalFooter(dbc.Button("Close", id="close-advanced-gdp", className="ms-auto", n_clicks=0))
        ], id="modal-advanced-gdp", size="xl", is_open=False),
    ])

@callback(
    [Output("tab2-view-mode-store", "data"),
     Output("btn-tab2-view-gdp", "color"),
     Output("btn-tab2-view-life", "color")],
    [Input("btn-tab2-view-gdp", "n_clicks"),
     Input("btn-tab2-view-life", "n_clicks")],
    prevent_initial_call=False
)
def update_view_buttons(n_gdp, n_life):
    trigger = ctx.triggered_id if ctx.triggered else None
    if trigger == "btn-tab2-view-life":
        return "life", "outline-primary", "primary"
    else:
        return "gdp", "primary", "outline-primary"

@callback(
    [Output("gdp-layout-container", "style"), Output("life-layout-container", "style"),
     Output("gdp-controls-row", "style")],
    Input("tab2-view-mode-store", "data")
)
def toggle_layouts(mode):
    if mode == "gdp":
        return {"display": "block"}, {"display": "none"}, {"display": "flex"}
    return {"display": "none"}, {"display": "block"}, {"display": "none"}

def _update_text(metric, view_type, view_mode):
    texts = {
        "map": {
            "title": {"gdp": {"total": "Economic Weight by Country", "capita": "Global GDP per Capita"}, 
                      "life": "Life Expectancy by Country"},
            "desc": {"gdp": {"total": "Largest economies (log10)", "capita": "Average wealth per person"}, 
                     "life": "Global longevity distribution"}
        },
        "lines": {
            "title": {"gdp": "History of the Selected Country", "life": "Life Expectancy Evolution"},
            "desc": {"gdp": "Time trend vs global average", "life": "Comparison with global average"}
        }
    }
    if view_mode == "life":
        return texts[metric]["title"]["life"], texts[metric]["desc"]["life"]
    if metric == "lines":
        return texts[metric]["title"]["gdp"], texts[metric]["desc"]["gdp"]
    return texts[metric]["title"]["gdp"][view_type], texts[metric]["desc"]["gdp"][view_type]

@callback(
    [Output("tab2-map-title-gdp", "children"), Output("tab2-map-description-gdp", "children"),
     Output("tab2-map-title-life", "children"), Output("tab2-map-description-life", "children"),
     Output("advanced-button-text", "children")],
    [Input("gdp-view", "value"), Input("tab2-view-mode-store", "data")]
)
def update_texts(view, mode):
    mt, md = _update_text("map", view, mode)
    btn = "Advanced Analysis: Health and Longevity" if mode=="life" else "Advanced Prosperity Analysis"
    return mt, md, mt, md, btn

def _create_stats_card(title, value, icon):
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div([html.I(className=f"bi {icon} fs-4 text-primary me-3"), 
                  html.Div([html.H6(title, className="mb-0 small text-muted"), html.H4(value, className="mb-0 fw-bold text-primary")], className="flex-grow-1")
        ], className="d-flex align-items-center")
    ], className="py-2 px-3"), className="shadow-sm"), width=4)

@callback(Output("gdp-stats-container", "children"),
          [Input("year-slider", "value"), Input('tabs', 'active_tab'), 
           Input("gdp-view", "value"), Input("tab2-view-mode-store", "data")])
def update_stats(yr, tab, view, mode):
    if tab != 'tab-2' or yr is None:
        return []
    if mode == "life":
        d = df_life_expectancy[df_life_expectancy["Year"]==yr].dropna(subset=["Life_Expectancy"])
        if d.empty:
            return []
        avg = d["Life_Expectancy"].mean()
        mx = d.loc[d["Life_Expectancy"].idxmax()]
        mn = d.loc[d["Life_Expectancy"].idxmin()]
        return [_create_stats_card("Global Average", f"{avg:.1f} years", "bi-globe"),
            _create_stats_card("Maximum", f"{mx['Life_Expectancy']:.0f} years ({mx['Country']})", "bi-arrow-up-circle"),
            _create_stats_card("Minimum", f"{mn['Life_Expectancy']:.0f} years ({mn['Country']})", "bi-arrow-down-circle")]
    d = _get_gdp_df(view)[lambda x: x["Year"]==yr].dropna(subset=["Value"])
    if d.empty:
        return []
    total = d["Value"].sum()
    mx = d.loc[d["Value"].idxmax()]
    cnt = len(d)
    unit = "Trillions USD" if view=="total" else "Thousand USD"
    fmt = f"${total/1e12:.1f}T" if view=="total" else f"${d['Value'].mean()/1e3:.1f}K avg"
    return [_create_stats_card("Total/Avg GDP" if view=="total" else "Avg GDP p.c.", fmt, "bi-cash-stack"),
            _create_stats_card("Largest Economy", f"{mx['Country']}", "bi-trophy"),
            _create_stats_card("Countries", str(cnt), "bi-pin-map")]

@callback([Output("gdp-map", "figure"), Output("gdp-map-life", "figure")],
          [Input("year-slider", "value"), Input("gdp-view", "value"), 
           Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_map(yr, view, tab, mode):
    empty = go.Figure()
    if tab != 'tab-2' or yr is None:
        return empty, empty
    if mode == "life":
        d = df_life_expectancy[lambda x: x["Year"]==yr].dropna(subset=["Life_Expectancy"])
        if d.empty:
            return empty, empty
        fig = px.choropleth(d, locations="ISOcode", color="Life_Expectancy", hover_name="Country",
                           hover_data={"Life_Expectancy": ":.1f", "ISOcode": False},
                           color_continuous_scale="RdYlGn", height=400)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Age", thickness=15, len=0.6),
            geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
            annotations=[dict(x=0.5, y=-0.1, xref='paper', yref='paper', text="Interactive: select a country >", showarrow=False, font=dict(size=12, color="gray"))])
        return fig, fig
    d = _get_gdp_df(view)[lambda x: (x["Year"]==yr) & (x["Value"]>0)].dropna(subset=["Value"])
    if d.empty:
        return empty, empty
    d["ColorValue"] = np.log10(d["Value"])
    fig = px.choropleth(d, locations="ISOcode", color="ColorValue", hover_name="Country",
                       hover_data={"Value": ":,.2f", "ColorValue": False},
                       color_continuous_scale="Viridis", height=550)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="log10(GDP)", thickness=15, len=0.6),
        geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
        annotations=[dict(x=0.5, y=-0.1, xref='paper', yref='paper', text="Interactive: select a country >", showarrow=False, font=dict(size=12, color="gray"))])
    return fig, fig

@callback([Output("gdp-country-total", "figure"), Output("selected-country-display", "children")],
          [Input("gdp-map", "clickData"), Input("year-slider", "value"), 
           Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_gdp_total(ck, yr, tab, mode):
    empty = go.Figure()
    if tab != 'tab-2' or yr is None or mode != "gdp":
        return empty, "Click on the map"
    iso = ck["points"][0].get("location") if ck and ck.get("points") else None
    dy = df_gdp_total[lambda x: x["Year"]==yr].dropna(subset=["Value"])
    if iso is None and not dy.empty:
        iso = dy.loc[dy["Value"].idxmax(), "ISOcode"]
    if iso is None:
        return empty, "Click on the map"
    c = df_gdp_total[lambda x: x["ISOcode"]==iso].dropna(subset=["Value"])
    if c.empty:
        return empty, "Click on the map"
    name = c["Country"].iloc[0]
    avg = df_gdp_total.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c["Year"], y=c["Value"], mode="lines+markers", name=name, line=dict(width=3, color='#3498db')))
    fig.add_trace(go.Scatter(x=avg["Year"], y=avg["Value"], mode="lines", name="Global Avg", line=dict(width=2, dash="dash", color='gray')))
    fig.add_vline(x=yr, line_width=1, line_dash="dot", line_color="red")
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>GDP: $%{y:,.0f}<extra></extra>")
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                     yaxis_title="Total GDP (USD)", xaxis_title="Year",
                     legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5, font=dict(size=9)))
    return fig, f"{name}"

@callback(Output("gdp-country-capita", "figure"),
          [Input("gdp-map", "clickData"), Input("year-slider", "value"), 
           Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_gdp_capita(ck, yr, tab, mode):
    empty = go.Figure()
    if tab != 'tab-2' or yr is None or mode != "gdp":
        return empty
    iso = ck["points"][0].get("location") if ck and ck.get("points") else None
    dy = df_gdp_capita[lambda x: x["Year"]==yr].dropna(subset=["Value"])
    if iso is None and not dy.empty:
        iso = dy.loc[dy["Value"].idxmax(), "ISOcode"]
    if iso is None:
        return empty
    c = df_gdp_capita[lambda x: x["ISOcode"]==iso].dropna(subset=["Value"])
    if c.empty:
        return empty
    name = c["Country"].iloc[0]
    avg = df_gdp_capita.dropna(subset=["Value"]).groupby("Year")["Value"].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c["Year"], y=c["Value"], mode="lines+markers", name=name, line=dict(width=3, color='#9b59b6')))
    fig.add_trace(go.Scatter(x=avg["Year"], y=avg["Value"], mode="lines", name="Global Avg", line=dict(width=2, dash="dash", color='gray')))
    fig.add_vline(x=yr, line_width=1, line_dash="dot", line_color="red")
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>GDP pc: $%{y:,.0f}<extra></extra>")
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                     yaxis_title="GDP per Capita (USD)", xaxis_title="Year",
                     legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5, font=dict(size=9)))
    return fig

@callback([Output("gdp-country-lines-life", "figure"), Output("tab2-lines-title-life", "children"), Output("tab2-lines-description-life", "children")],
          [Input("gdp-map-life", "clickData"), Input("year-slider", "value"), 
           Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_life_lines(ck, yr, tab, mode):
    empty = go.Figure()
    if tab != 'tab-2' or yr is None or mode != "life":
        return empty, "Life Expectancy Evolution", "Life expectancy history"
    iso = ck["points"][0].get("location") if ck and ck.get("points") else None
    dy = df_life_expectancy[lambda x: x["Year"]==yr].dropna(subset=["Life_Expectancy"])
    if iso is None and not dy.empty:
        iso = dy.loc[dy["Life_Expectancy"].idxmax(), "ISOcode"]
    if iso is None:
        return empty, "Life Expectancy Evolution", "Life expectancy history"
    c = df_life_expectancy[lambda x: x["ISOcode"]==iso].dropna(subset=["Life_Expectancy"])
    if c.empty:
        return empty, "Life Expectancy Evolution", "Life expectancy history"
    name = c["Country"].iloc[0]
    avg = df_life_expectancy.dropna(subset=["Life_Expectancy"]).groupby("Year")["Life_Expectancy"].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c["Year"], y=c["Life_Expectancy"], mode="lines", name=name, line=dict(width=3, color='#2ecc71')))
    fig.add_trace(go.Scatter(x=avg["Year"], y=avg["Life_Expectancy"], mode="lines", name="Global Average", line=dict(width=2, dash="dash", color='gray')))
    fig.add_vline(x=yr, line_width=1, line_dash="dot", line_color="red")
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Life Exp: %{y:.1f} years<extra></extra>")
    fig.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                     yaxis_title="Life Expectancy (years)", xaxis_title="Year",
                     legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10)))
    return fig, f"Life Expectancy - {name}", f"Historical evolution of {name}"

@callback(Output("tab2-continental-chart-container", "children"),
          [Input("year-slider", "value"), Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_continental_life(yr, tab, mode):
    if tab != 'tab-2' or yr is None or mode != "life":
        return None
    all_data = df_life_expectancy.dropna(subset=["Life_Expectancy"]).copy()
    all_data["Continent"] = all_data["ISOcode"].map(ISO_TO_REGION).fillna("Other")
    all_data = all_data[all_data["Continent"] != "Other"]
    cont_avg = all_data.groupby(["Continent", "Year"])["Life_Expectancy"].mean().reset_index()
    
    fig = px.line(cont_avg, x="Year", y="Life_Expectancy", color="Continent",
                 line_shape="linear", markers=False)
    fig.add_vline(x=yr, line_width=2, line_dash="solid", line_color="red",
                 annotation_text=f"Year {yr}", annotation_position="top right")
    fig.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10), 
                     xaxis_title="Year", yaxis_title="Life Expectancy (years)",
                     hovermode="x unified",
                     legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5))
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Life: %{y:.1f} years<extra></extra>")
    return dbc.Card(dbc.CardBody([
        html.H5("Continental Progress", className="text-primary fw-bold mb-1"),
        html.P("Time evolution of life expectancy by continent.", className="text-muted small mb-2"),
        dcc.Graph(figure=fig)
    ], className="py-2 px-2"), className="shadow-sm")

@callback(Output("modal-advanced-gdp", "is_open"),
          [Input("advanced-button-text", "n_clicks"), Input("close-advanced-gdp", "n_clicks")],
          State("modal-advanced-gdp", "is_open"))
def toggle_modal(n1, n2, is_open):
    return not is_open if (n1 or n2) else is_open

@callback(Output("modal-advanced-body-gdp", "children"),
          [Input("year-slider", "value"), Input('tabs', 'active_tab'), Input("tab2-view-mode-store", "data")])
def update_modal(yr, tab, mode):
    if tab != 'tab-2' or yr is None:
        return None
    return create_life_expectancy_advanced_analysis(yr) if mode=="life" else create_gdp_advanced_analysis(yr)

def _create_treemap(data, value_col, color_scale):
    return px.treemap(data, path=['Country'], values=value_col, color=value_col,
                     color_continuous_scale=color_scale, template="plotly_white")

def _create_lollipop(data, x_col, y_col, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data[x_col], y=data[y_col], mode='markers',
                            marker=dict(size=12, color=color), name=""))
    shapes = [dict(type="line", xref="x", yref="y", x0=0, y0=row[y_col], x1=row[x_col], y1=row[y_col],
                  line=dict(color="lightgray", width=2)) for _, row in data.iterrows()]
    fig.update_layout(shapes=shapes, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig

def create_gdp_advanced_analysis(yr):
    d1 = df_gdp_total[lambda x: x["Year"]==yr].dropna(subset=["Value"])
    fig1 = _create_treemap(d1.nlargest(15, "Value"), 'Value', 'Viridis')
    
    d2 = df_gdp_capita[lambda x: x["Year"]==yr].dropna(subset=["Value"])
    top = d2.nlargest(10, "Value").sort_values("Value")
    fig2 = _create_lollipop(top, "Value", "Country", 'mediumturquoise')
    fig2.update_layout(xaxis=dict(title="GDP per Capita ($)"), yaxis=dict(title=""))
    
    hist = df_gdp_total[lambda x: (x["Year"]<=yr) & (x["Value"]>0)].sort_values(["ISOcode", "Year"])
    hist["pct_yoy"] = hist.groupby("ISOcode")["Value"].pct_change() * 100
    name_map = hist.groupby("ISOcode")["Country"].first().to_dict()
    rr = hist.groupby("ISOcode")["pct_yoy"].agg(['mean', 'std']).dropna()
    rr.columns = ['Avg_Growth', 'Volatility']
    rr["Country"] = rr.index.map(name_map)
    rr = rr[rr['Avg_Growth'] < 50]
    fig3 = px.scatter(rr, x="Avg_Growth", y="Volatility", hover_name="Country", size="Volatility",
                     labels={"Avg_Growth": "Avg Growth (%)", "Volatility": "Volatility (Std Dev)"},
                     template="plotly_white")
    fig3.add_hline(y=rr['Volatility'].median(), line_dash="dash", line_color="gray")
    fig3.add_vline(x=0, line_color="gray")
    
    std_dev = hist.groupby("ISOcode")["pct_yoy"].std()
    top_vol = std_dev.nlargest(10).index
    df_vol = hist[hist["ISOcode"].isin(top_vol)]
    stats = df_vol.groupby("Country")["pct_yoy"].agg(['min', 'max']).reset_index()
    stats['range'] = stats['max'] - stats['min']
    stats = stats.sort_values('range')
    fig4 = go.Figure()
    for _, row in stats.iterrows():
        fig4.add_trace(go.Scatter(x=[row['min'], row['max']], y=[row['Country'], row['Country']],
                                 mode='lines', line=dict(color='lightgray', width=3), showlegend=False, hoverinfo='skip'))
    fig4.add_trace(go.Scatter(x=stats['min'], y=stats['Country'], mode='markers', name='Min Growth',
                             marker=dict(color='#e74c3c', size=10), hovertemplate='%{y}: Min %{x:.1f}%<extra></extra>'))
    fig4.add_trace(go.Scatter(x=stats['max'], y=stats['Country'], mode='markers', name='Max Growth',
                             marker=dict(color='#2ecc71', size=10), hovertemplate='%{y}: Max %{x:.1f}%<extra></extra>'))
    fig4.update_layout(xaxis_title="Annual Growth (%)", template="plotly_white",
                      margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2), hovermode="closest")
    
    for f in [fig1, fig2, fig3, fig4]:
        f.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    
    return html.Div([
        dbc.Row([
            dbc.Col([html.H6("Global Economic Weight", className="text-primary fw-bold"),
                html.P("Who dominates the economy?", className="text-muted small"), dcc.Graph(figure=fig1)], width=6),
            dbc.Col([html.H6("Top Per Capita Wealth", className="text-primary fw-bold"),
                html.P("Ranking of the richest nations.", className="text-muted small"), dcc.Graph(figure=fig2)], width=6),
        ], className="g-3 mb-4"),
        dbc.Row([
            dbc.Col([html.H6("Risk vs Return", className="text-primary fw-bold"),
                html.P("Average growth vs instability.", className="text-muted small"), dcc.Graph(figure=fig3)], width=6),
            dbc.Col([html.H6("Volatility Ranges", className="text-primary fw-bold"),
                html.P("Distance between best and worst year.", className="text-muted small"), dcc.Graph(figure=fig4)], width=6),
        ], className="g-3"),
    ])

def create_life_expectancy_advanced_analysis(yr):
    d1 = df_life_expectancy[lambda x: x["Year"]==yr].dropna(subset=["Life_Expectancy"])
    fig1 = _create_treemap(d1.nlargest(15, "Life_Expectancy"), 'Life_Expectancy', 'RdYlGn')
    
    bottom = d1.nsmallest(10, "Life_Expectancy").sort_values("Life_Expectancy")
    fig2 = _create_lollipop(bottom, "Life_Expectancy", "Country", '#e74c3c')
    fig2.update_layout(xaxis=dict(title="Life Expectancy (years)"), yaxis=dict(title=""))
    
    dw = d1.copy()
    dw["Region"] = dw["ISOcode"].map(ISO_TO_REGION).fillna("Other")
    dw = dw[dw["Region"] != "Other"]
    fig3 = px.box(dw, x="Region", y="Life_Expectancy", color="Region", template="plotly_white", points="all")
    fig3.update_layout(showlegend=False, xaxis_tickangle=-45)
    
    fig4 = px.histogram(d1, x="Life_Expectancy", nbins=30, template="plotly_white", color_discrete_sequence=['#3498db'])
    fig4.update_layout(xaxis_title="Life Expectancy (years)", yaxis_title="Number of Countries", showlegend=False)
    mean_life = d1["Life_Expectancy"].mean()
    fig4.add_vline(x=mean_life, line_dash="dash", line_color="red",
                  annotation_text=f"Average: {mean_life:.1f}", annotation_position="top right")
    
    for f in [fig1, fig2, fig3, fig4]:
        f.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    
    return html.Div([
        dbc.Row([
            dbc.Col([html.H6("Top Life Expectancy", className="text-primary fw-bold"),
                html.P("Countries with the healthiest populations.", className="text-muted small"), dcc.Graph(figure=fig1)], width=6),
            dbc.Col([html.H6("Lowest Life Expectancy", className="text-primary fw-bold"),
                html.P("Countries with greater health challenges.", className="text-muted small"), dcc.Graph(figure=fig2)], width=6),
        ], className="g-3 mb-4"),
        dbc.Row([
            dbc.Col([html.H6("Regional Distribution", className="text-primary fw-bold"),
                html.P("Variation within and between regions.", className="text-muted small"), dcc.Graph(figure=fig3)], width=6),
            dbc.Col([html.H6("Global Distribution", className="text-primary fw-bold"),
                html.P("Number of countries by age range.", className="text-muted small"), dcc.Graph(figure=fig4)], width=6),
        ], className="g-3"),
    ])
