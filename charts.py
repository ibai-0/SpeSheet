from dash import html, dcc, dash_table, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from prepare_data import df_totals, df_capita, df_sectors, df_correlation, df_cumulative

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