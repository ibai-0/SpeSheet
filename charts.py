from dash import html, dcc, dash_table, callback, Input, Output, State  # <-- Añade State aquíimport dash_bootstrap_components as dbc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
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
    Output('year-slider', 'value'),
    Input('auto-stepper', 'n_intervals'),
    State('year-slider', 'value'),
    State('year-slider', 'max'),
    State('year-slider', 'min'),
    prevent_initial_call=True
)
def animate_slider(n, current_year, max_y, min_y):
    # Si llega al final, vuelve a empezar
    return current_year + 1 if current_year < max_y else min_y



@callback(
    Output('auto-stepper', 'disabled'),
    Output('play-button', 'children'),
    Input('play-button', 'n_clicks'),
    State('auto-stepper', 'disabled')
)
def toggle_play(n, is_disabled):
    if n % 2 == 0:
        return True, "▶ Reproducir Histórico"
    return False, "⏸ Pausar"

# Modificación del render_content para el layout A | B/C
@callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'active_tab'),
    Input('year-slider', 'value')
)
def render_content(tab, selected_year):
    if tab == 'tab-1':
        dff = df_totals[df_totals['Year'] == selected_year]
        
        # A: Mapa Mundi con ID para interactividad
        fig_map = px.choropleth(
            dff, locations="ISOcode", color="Value", hover_name="Country",
            color_continuous_scale="Viridis", height=600
        )
        fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0}, transition_duration=500)

        # B: Enfoque Big 3 (China, USA, India)
        # Filtramos directamente por códigos ISO
        big3_df = dff[dff['ISOcode'].isin(['CHN', 'USA', 'IND'])].sort_values('Value', ascending=False)
        fig_big3 = px.bar(
            big3_df, x='ISOcode', y='Value', color='ISOcode',
            title="Emisiones Big 3 (Mt)",
            color_discrete_map={'CHN': '#e74c3c', 'USA': '#3498db', 'IND': '#f1c40f'}
        )
        fig_big3.update_layout(showlegend=False, height=280, margin={"t":40,"b":20})

        # C: Tendencia del Top emisor actual (Mini line chart)
        top_country = dff.loc[dff['Value'].idxmax()]['Country']
        dff_trend = df_cumulative[(df_cumulative['Country'] == top_country) & (df_cumulative['Year'] <= selected_year)]
        
        fig_mini = px.line(dff_trend, x="Year", y="Value", title=f"Histórico: {top_country}")
        fig_mini.update_layout(height=280, margin={"t":40,"b":20}, xaxis_title=None, yaxis_title=None)

        return html.Div(className='tab-animacion', children=[
            dbc.Row([
                # Columna A (Izquierda) - Mapa
                dbc.Col(dcc.Graph(id='map-graph', figure=fig_map), width=8),
                
                # Columna B/C (Derecha) - Subplots
                dbc.Col([
                    dbc.Row(dbc.Col(dcc.Graph(figure=fig_big3), width=12)),
                    dbc.Row(dbc.Col(dcc.Graph(figure=fig_mini), width=12)),
                ], width=4)
            ])
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

    # Dentro del callback render_content en charts.py
    elif tab == 'tab-4':
        # 1. Datos año actual y año base
        dff_now = df_totals[df_totals['Year'] == selected_year].copy()
        df_1970 = df_totals[df_totals['Year'] == 1970][['Country', 'Value']].rename(columns={'Value': 'Value_1970'})
        
        dff_rel = pd.merge(dff_now, df_1970, on='Country')
        dff_rel = dff_rel[dff_rel['Value_1970'] > 0]
        dff_rel['Growth_Factor'] = dff_rel['Value'] / dff_rel['Value_1970']
        
        # --- TRANSFORMACIÓN COMPLEJA: Perfiles de Emisiones (Spider Chart) ---
        # 1. Deuda Acumulada
        df_cumulative = df_totals[df_totals['Year'] <= selected_year].groupby('Country')['Value'].sum().reset_index()
        df_cumulative.columns = ['Country', 'Cumulative_Value']
        
        # 2. Unimos todo para el Top 5 países del año actual
        top5_countries = dff_now.nlargest(5, 'Value')['Country'].tolist()
        df_spider_raw = pd.merge(dff_rel, df_cumulative, on='Country')
        df_spider = df_spider_raw[df_spider_raw['Country'].isin(top5_countries)].copy()

        # Normalizamos los datos (0 a 1) para que se puedan comparar en el radar
        for col in ['Value', 'Growth_Factor', 'Cumulative_Value']:
            df_spider[col] = df_spider[col] / df_spider[col].max()

        # Convertimos a formato largo (melt) para el gráfico de radar
        df_radar = df_spider.melt(id_vars='Country', value_vars=['Value', 'Growth_Factor', 'Cumulative_Value'],
                                  var_name='Métrica', value_name='Proporción')

        # --- FIGURA A: TREEMAP (Ancho completo) ---
        fig_tree = px.treemap(
            dff_now,
            path=[px.Constant("Mundo"), 'Continent', 'Country'],
            values='Value',
            color='Continent',
            color_discrete_sequence=px.colors.qualitative.Prism,
            title=f"Distribución Jerárquica de Emisiones ({selected_year})"
        )
        fig_tree.update_traces(textinfo="label+value", texttemplate="<b>%{label}</b><br>%{value:.1f} Mt")
        fig_tree.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=450)

        # --- FIGURA B: DOT PLOT (Centrado y más estrecho) ---
        fig_scatter = px.scatter(
            dff_rel, 
            x="Continent", 
            y="Growth_Factor", 
            color="Continent",
            size="Value",
            hover_name="Country",
            log_y=True,
            size_max=40, # Burbujas grandes
            title="Evolución vs 1970"
        )

        fig_scatter.add_hline(y=1, line_dash="dash", line_color="red")
        
        # Ajustamos el margen para que no se vea pegado a los bordes
        fig_scatter.update_layout(margin=dict(t=50, l=10, r=10, b=10), height=400, showlegend=False)
        
        # --- FIGURA C: SPIDER CHART (Gráfico de Radar) ---
        fig_radar = px.line_polar(
            df_radar, r='Proporción', theta='Métrica', color='Country',
            line_close=True, template="plotly_dark",
            title=f"Perfiles de los Top 5 Emisores ({selected_year})"
        )
        fig_radar.update_traces(fill='toself')
        fig_radar.update_layout(margin=dict(t=50, l=10, r=10, b=10), height=400)

        # --- LAYOUT FINAL ---
        return html.Div([
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_tree)], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([dcc.Graph(figure=fig_scatter)], width=6),
                dbc.Col([dcc.Graph(figure=fig_radar)], width=6)
            ])
        ])
        
    
@callback(
    Output('tabs', 'active_tab'),
    Input('map-graph', 'clickData'), # Asegúrate de poner id='map-graph' al dcc.Graph del mapa
    prevent_initial_call=True
)
def go_to_country_detail(clickData):
    if clickData:
        # Al hacer click, saltamos a la pestaña de detalles (ej. tab-3)
        return 'tab-3'
    return 'tab-1'