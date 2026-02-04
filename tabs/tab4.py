from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from prepare_data import df_totals
from components import controls 

def layout():
    return html.Div(className='tab-animacion', children=[
        # Keep the shared year slider from components
        controls.layout(), 
        # Container where charts are injected by the callback
        html.Div(id='tab4-charts-container') 
    ])

@callback(
    Output('tab4-charts-container', 'children'),
    Input('year-slider', 'value') # Listen to the slider in controls.py
)
def update_tab4_graphics(selected_year):
    if selected_year is None:
        return html.Div("Select a year to view analysis", className="text-center mt-5")

    # 1. Data preparation for the three charts
    # Filter main data for the selected year
    dff_now = df_totals[df_totals['Year'] == selected_year].copy()
    # Get 1970 data as a baseline for growth comparison
    df_1970 = df_totals[df_totals['Year'] == 1970][['Country', 'Value']].rename(columns={'Value': 'Value_1970'})
    
    # Merge and calculate the growth multiplier relative to 1970
    dff_rel = pd.merge(dff_now, df_1970, on='Country')
    dff_rel = dff_rel[dff_rel['Value_1970'] > 0] # Filter out zero values to avoid division errors
    dff_rel['Growth_Multiplier'] = dff_rel['Value'] / dff_rel['Value_1970']
    
    # 2. Spider Chart Logic (Radar)
    # Calculate cumulative emissions up to the selected year
    df_cumulative_sum = df_totals[df_totals['Year'] <= selected_year].groupby('Country')['Value'].sum().reset_index()
    df_cumulative_sum.columns = ['Country', 'Cumulative_Debt']
    
    # Identify the Top 5 emitters for the current year
    top5_list = dff_now.nlargest(5, 'Value')['Country'].tolist()
    df_spider = pd.merge(dff_rel, df_cumulative_sum, on='Country')
    df_spider = df_spider[df_spider['Country'].isin(top5_list)].copy()

    # Normalize metrics between 0 and 1 for visual comparison in the radar chart
    for col in ['Value', 'Growth_Multiplier', 'Cumulative_Debt']:
        if not df_spider.empty and df_spider[col].max() > 0:
            df_spider[col] = df_spider[col] / df_spider[col].max()

    # Pivot data to long format for Plotly Express line_polar
    df_radar = df_spider.melt(id_vars='Country', 
                              value_vars=['Value', 'Growth_Multiplier', 'Cumulative_Debt'],
                              var_name='Metric', value_name='Score')

    # --- CHART GENERATION ---
    
    # Emissions Tree Map: Shows hierarchy of Continent > Country
    fig_tree = px.treemap(
        dff_now, path=[px.Constant("World"), 'Continent', 'Country'],
        values='Value', color='Continent',
        title=f"Emissions Tree Map ({selected_year})"
    )
    
    # Scatter Plot: Shows growth vs. absolute emissions by continent
    fig_scatter = px.scatter(
        dff_rel, x="Continent", y="Growth_Multiplier", color="Continent",
        size="Value", hover_name="Country", log_y=True,
        title="Evolution Multiplier (Base 1970)"
    )

    # Radar Chart: Profiles the Top 5 Emitters based on normalized scores
    fig_radar = px.line_polar(
        df_radar, r='Score', theta='Metric', color='Country',
        line_close=True, title="Top 5 Emitter Profiles"
    )

    # Return charts arranged in a grid
    return [
        dbc.Row([dbc.Col([dcc.Graph(figure=fig_tree)], width=12)], className="mb-4"),
        dbc.Row([
            dbc.Col([dcc.Graph(figure=fig_scatter)], width=6),
            dbc.Col([dcc.Graph(figure=fig_radar)], width=6)
        ])
    ]