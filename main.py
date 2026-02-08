import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, callback, no_update
from prepare_data import min_year, max_year
import charts 

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server

app.layout = dbc.Container([

    ## Title
    dbc.Row([
        dbc.Col(html.H1("ALLSTAT: CO2 Emissions Dashboard", className="text-center mt-2 mb-1", style={'color': '#2c3e50', 'fontWeight': 'bold'}), width=12),
        dbc.Col(html.P("Advanced spatio-temporal data analysis for official statistics", 
                        className="text-center text-muted mb-3 small"), width=12),
    ]),

    # Tab Section
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label='Emissions Map', tab_id='tab-1'),
                dbc.Tab(label='Nation Prosperity', tab_id='tab-2'),
                dbc.Tab(label='Correlation Emission Prosperity', tab_id='tab-3'),
            ], id="tabs", active_tab='tab-1', className="mb-2 nav-justified"),
        ], width=12)
    ]),

    # Global stores so callbacks that reference subtab stores exist at initial load
    dcc.Store(id='tab2-view-mode-store', data='gdp'),
    dcc.Store(id='tab3-view-mode-store', data='gdp'),

    # Controls and Visualization
    dbc.Row([
        dbc.Col([
            html.Div(id='tabs-content', className="mt-2")
        ], width=12)
    ]),

    # Dynamics Conclusion Section (Updates based on active tab)
    dbc.Row([
        dbc.Col(html.Div(id='tab-conclusion-container', className="mt-4 mb-2"), width=12)
    ]),

    # Pie de página con créditos del grupo
    html.Footer(
        dbc.Row(
            dbc.Col(html.P("© 2026 Ibai Mayoral - Hugo Recio - Iñaki Moreno - Xabier Aranguena", 
                        className="text-center mt-5 text-secondary small"))
        )
    )
], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

@callback(
    Output('tab-conclusion-container', 'children'),
    [Input('tabs', 'active_tab'),
     Input('tab2-view-mode-store', 'data'),
     Input('tab3-view-mode-store', 'data')]
)
def update_tab_conclusion(active_tab, tab2_view_mode, tab3_view_mode):
    """Render an analytical summary that is aware of sub-views (subtabs)."""
    default_text = "Explore the data to extract meaningful patterns."

    conclusions = {
        'tab-1': """The two primary graphics in this tab illustrate the global evolution of total CO2 emissions. The World Map displays the annual emissions volume per country. It is clearly visible that, over the last 50 years, nations such as China and India have matched or surpassed the major emitters of half a century ago, like the USA and Russia.

The treemap, categorized by region, highlights that Europe and North America, the dominant emitters of the 20th century, have been overtaken in the 21st century by growing economies in developing regions, such as East/South Asia and the Middle East. This change is attributed to the environmental restrictions implemented by developed nations to reduce their impact, in contrast to the rapid and high-pollution industrialization seen in other regions.

An individual analysis for each country can be performed by clicking on the map, which reveals the main emitting industries and their growth over the years. The evolution of emissions per capita indicates whether a country has made efforts to reduce its environmental footprint or if it is growing so rapidly that no reductions have been achieved. Furthermore, the selected country is compared in terms of growth, current emissions, and emission debt against the global top five emitters. This comparison highlights the country's relevance in total emission volume and its growth trajectory relative to others.

A similar analysis is applied globally. Regarding sectoral emissions, it is evident that the transport and power industries have gained significant importance in the current century, with their emissions increasing exponentially. According to emissions per capita, the 1970s was the most polluting decade, however, that was also when developed countries gained awareness of the resulting environmental issues. Over the next two decades, emissions were considerably reduced. However, with the rise of developing nations, emissions nearly peaked again in the 2010s. From that point until the COVID-19 pandemic, considerable efforts were made to reduce emissions, reaching the lowest figures in 50 years. Finally, the top 5 global emitters radar plot clearly illustrates that China and India have surpassed traditional industrial nations in total emissions, while the USA continues to lead in emission debt.""",

        'tab-2': {
            'gdp': """The World Map displayed in this tab shows the yearly evolution of GDP and GDP per capita for every country. It is clearly visible that developing industries in Asia have caught up with traditional industries in terms of total production. On the right side, two histograms illustrate the growth of the GDP data for a specific country, which can be selected by clicking on the map.

For a deeper insight, the advanced analysis section features two plots at the top that highlight the most productive countries (GDP) and those with the wealthiest individuals (GDP per capita). The treemap clearly demonstrates the growth of the Asian giants, while the bar plot shows that oil-exporting Middle Eastern countries have caught up to the wealthiest European nations in terms of GDP per capita.

However, many economically growing countries depend on volatile goods or industries, making them more unstable than the major global powers. Notable examples include African states such as Equatorial Guinea and Liberia, as well as Middle Eastern oil-exporting nations.""",
            
            'life': """The World Map in this section showcases the evolution of life expectancy over the last 50 years. This progression is clearly correlated with economic growth, particularly with the increase in individual wealth. The data demonstrates that countries with a high total GDP but low GDP per capita often have lower life expectancy than smaller, wealthier nations.

In the bottom-left diagram, a country can be selected to track its life expectancy evolution over the years and compare it to the world average. This comparison indicates whether a country’s quality of life is improving or declining relative to global standards.

The graphic on the bottom-right displays the average life expectancy by region, allowing for a direct comparison of their historical evolution. It is clearly visible that Europe and North America lead in life expectancy values. However, the data also highlights that South Asia has maintained significant and consistent growth in this metric over the decades."""
        },

        'tab-3': {
            'gdp': """To demonstrate the correlation between wealth and pollution, the primary graphic is a scatter plot where the size of the dots represents population. This plot maps each country's individual wealth against its CO2 emissions. As observed, both metrics are highly correlated, reaching an average coefficient of 0.8. This suggests that wealthier individuals tend to have higher pollution footprints.

By clicking on a specific country, a detailed plot appears showing the evolution of these metrics over time. For example, European countries have managed to increase wealth while decreasing emissions, whereas Asian countries are currently seeing an increase in both.

A deeper analysis requires a distinction between green growth and dirty growth. "Green growth" occurs when a country increases its wealth while simultaneously reducing its pollutant output. In contrast, "dirty growth" describes a rise in wealth accompanied by a significant increase in pollution. In this scatter plot, it is clearly visible that regions and countries that have prioritized emission reductions, such as the European Union, North America, and Japan, fall within the green growth zone. Conversely, many currently developing countries in Africa and South Asia are experiencing economic expansion without significantly mitigating contamination.""",
            
            'life': """The correlation between life expectancy and pollution is demonstrated through a primary scatter plot that compares life expectancy against CO2 emissions per capita for every country. While the correlation is not as strong as it is with wealth, an average coefficient of 0.7 clearly indicates a significant relationship between these two metrics. Furthermore, the individual evolution of these metrics for each country can be viewed in a detailed plot by clicking on the corresponding bubble.

To provide a deeper analysis, we differentiate between high-cost progress and sustainable progress. High-cost progress is when a country successfully improves life expectancy but at the expense of increasing pollution. While sustainable progress is when a country improves both life quality and emission reductions simultaneously.

In the scatter plot, a clear distinction is visible between North America and Europe versus developing regions. People in more developed nations are seeing gains in health alongside increased environmental awareness. In contrast, many developing countries are achieving health improvements by polluting more. However, some African nations are leading the way in life expectancy growth within the sustainable progress zone. For instance, countries like Angola, Eritrea, and Liberia have managed to decrease pollution while increasing life expectancy over specific 20-year periods within the last half-century."""
        }
    }

    tab2_view_mode = tab2_view_mode or 'gdp'
    tab3_view_mode = tab3_view_mode or 'gdp'
    if active_tab == 'tab-2':
        insight_text = conclusions['tab-2'].get(tab2_view_mode, default_text)
    elif active_tab == 'tab-3':
        insight_text = conclusions['tab-3'].get(tab3_view_mode, default_text)
    else:
        insight_text = conclusions.get(active_tab, default_text)

    return dbc.Card(dbc.CardBody([
        html.H6([
            html.I(className="bi bi-lightbulb-fill me-2"),
            "Key Research Insight"
        ], className="text-primary fw-bold mb-2"),
        html.P(insight_text, className="mb-0 text-dark fst-italic", style={'whiteSpace': 'pre-wrap'})
    ]), className="shadow-sm border-0", style={'backgroundColor': '#eef2f7'})


if __name__ == '__main__':
    app.run_server(debug=False)

