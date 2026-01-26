import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table

# --- 1. DATA PREPARATION ---
file_path = 'CO2.xlsx'
xl = pd.ExcelFile(file_path)

def safe_load_and_melt(keyword, id_vars):
    sheet_name = next((s for s in xl.sheet_names if keyword.lower() in s.lower()), None)
    if sheet_name:
        df = xl.parse(sheet_name)
        df.columns = [str(col) for col in df.columns]
        df_melted = df.melt(id_vars=id_vars, var_name='Year', value_name='Value')
        df_melted['Year'] = pd.to_numeric(df_melted['Year'], errors='coerce')
        return df_melted.dropna(subset=['Year'])
    return pd.DataFrame()

# Load your specific sheets
df_totals = safe_load_and_melt('totals', ['Country', 'ISOcode'])
df_capita = safe_load_and_melt('capita', ['Country', 'ISOcode'])
df_sectors = safe_load_and_melt('sector', ['Country', 'ISOcode', 'Sector'])

# --- 2. APP SETUP ---
app = Dash(__name__)

app.layout = html.Div([
    html.H1("ALLSTAT: CO2 Emissions Dashboard Prototype", style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Summary Statistics Bar (Requirement 2.1 & 2.2)
    html.Div(id='stats-container', style={'display': 'flex', 'justifyContent': 'space-around', 'padding': '20px', 'backgroundColor': '#f4f4f4', 'borderRadius': '10px'}),

    dcc.Tabs(id="tabs", value='tab-1', children=[
        dcc.Tab(label='Emissions Map', value='tab-1'),
        dcc.Tab(label='Sector Breakdown', value='tab-2'),
        dcc.Tab(label='Per Capita Rank', value='tab-3'),
        dcc.Tab(label='Data Explorer', value='tab-4'),
    ]),

    html.Div([
        html.Br(),
        html.Label("Year Selector:", style={'fontWeight': 'bold'}),
        dcc.Slider(
            id='year-slider',
            min=int(df_totals['Year'].min()),
            max=int(df_totals['Year'].max()),
            value=int(df_totals['Year'].max()),
            marks={str(y): str(y) for y in range(1970, 2026, 10)},
            step=1
        ),
    ], style={'padding': '20px'}),

    html.Div(id='tabs-content')
])

# --- 3. CALLBACKS ---

# Callback for Statistics (Requirement 2.1)
@app.callback(
    Output('stats-container', 'children'),
    Input('year-slider', 'value')
)
def update_stats(selected_year):
    dff = df_totals[df_totals['Year'] == selected_year]
    global_sum = dff['Value'].sum()
    max_row = dff.loc[dff['Value'].idxmax()]
    
    return [
        html.Div([html.B(f"Global Total ({selected_year}): "), f"{global_sum:,.2f} Mt CO2"]),
        html.Div([html.B("Top Emitter: "), f"{max_row['Country']} ({max_row['Value']:,.2f} Mt)"]),
        html.Div([html.B("Average per Country: "), f"{dff['Value'].mean():,.2f} Mt"])
    ]

# Callback for Content
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value'),
    Input('year-slider', 'value')
)
def render_content(tab, selected_year):
    if tab == 'tab-1':
        dff = df_totals[df_totals['Year'] == selected_year]
        fig = px.choropleth(dff, locations="ISOcode", color="Value", hover_name="Country", 
                           color_continuous_scale="Viridis", title="World CO2 Distribution")
        return dcc.Graph(figure=fig)

    elif tab == 'tab-2':
        dff = df_sectors[df_sectors['Year'] == selected_year]
        fig = px.sunburst(dff, path=['Country', 'Sector'], values='Value', title="Emissions by Sector")
        return dcc.Graph(figure=fig)

    elif tab == 'tab-3':
        dff = df_capita[df_capita['Year'] == selected_year].sort_values('Value', ascending=False).head(20)
        fig = px.bar(dff, x='Value', y='Country', orientation='h', title="Top 20 Per Capita")
        return dcc.Graph(figure=fig)

    elif tab == 'tab-4':
        dff = df_totals[df_totals['Year'] == selected_year]
        return html.Div([
            dash_table.DataTable(
                data=dff.to_dict('records'),
                columns=[{"name": i, "id": i} for i in dff.columns],
                sort_action="native",
                filter_action="native",
                page_size=15,
                style_table={'height': '400px', 'overflowY': 'auto'}
            )
        ], style={'padding': '20px'})

if __name__ == '__main__':
    # FIXED: Use app.run instead of app.run_server
    app.run(debug=True)