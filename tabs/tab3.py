from dash import html, dcc, callback, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from prepare_data import df_totals, df_capita, df_gdp_total, df_gdp_capita, min_year, max_year, ISO_TO_REGION
from components import controls

def layout():
    return html.Div(className='tab-animacion', children=[
        
        controls.layout(),

        dbc.Row([
            # -------------------------------------------------------------
            # COLUMNA PRINCIPAL (IZQUIERDA) - 8/12
            # El Gráfico de Correlación (Burbujas) es ahora el PROTAGONISTA
            # -------------------------------------------------------------
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5("Wealth vs. CO₂ Emissions (Global Correlation)", className="card-title text-primary"),
                    html.P("Does being richer mean being dirtier? Click on a bubble to trace that country's history.", 
                           className="card-subtitle text-muted small mb-2"),
                    dcc.Graph(id='corr-bubble-graph', style={'height': '600px'}) # Más alto para destacar
                ]), className="shadow-sm h-100")
            ], width=8),
            
            # -------------------------------------------------------------
            # COLUMNA LATERAL (DERECHA) - 4/12
            # Estadísticas, Trayectoria y Botón
            # -------------------------------------------------------------
            dbc.Col([
                # 1. Tarjeta de Estadísticas (Correlación del año)
                dbc.Card(dbc.CardBody([
                    html.H6("Global Correlation (Pearson r)", className="text-muted small mb-1"),
                    html.H2(id="corr-value-display", className="text-center my-2 fw-bold text-dark"),
                    html.P(id="corr-explanation-display", className="text-center text-muted small mb-0")
                ]), className="shadow-sm mb-3"),

                # 2. Gráfico de Trayectoria (Historia del país)
                dbc.Card(dbc.CardBody([
                    html.H6("Development Path (1960-2024)", className="card-subtitle text-muted mb-2"),
                    dcc.Graph(id='corr-trajectory-graph', style={'height': '250px'}),
                    html.Small("Log-Log scale to visualize development stages.", className="text-muted d-block text-end mt-1")
                ]), className="shadow-sm mb-3"),

                # 3. Botón de Análisis Avanzado (Integrado y elegante)
                dbc.Card(dbc.CardBody([
                    html.H6("Deep Dive", className="card-subtitle text-muted mb-2"),
                    html.P("Analyze the 'Decoupling' phenomenon: Growing GDP while reducing CO₂.", className="small text-secondary"),
                    dbc.Button(
                        "📉 Open Decoupling Analysis",
                        id="corr-open-advanced",
                        color="dark",
                        outline=False,
                        className="w-100 shadow-sm",
                        size="md"
                    )
                ]), className="shadow-sm"),
                
            ], width=4),
        ]),
        
        # -------------------------------------------------------------
        # MODAL AVANZADO (DESACOPLE)
        # -------------------------------------------------------------
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Decoupling Analysis: Breaking the Link")),
            dbc.ModalBody([
                html.P("This chart compares GDP growth vs. CO₂ growth over the selected period. Ideally, countries should land in the 'Green Growth' zone.", className="text-muted small"),
                dcc.Graph(id="corr-decoupling-graph"),
            ]),
            dbc.ModalFooter(
                dbc.Button("Close Analysis", id="corr-close-advanced", color="secondary", size="sm")
            ),
        ], id="corr-modal-advanced", size="xl", centered=True, is_open=False),

        # Store para guardar país seleccionado
        dcc.Store(id="corr-selected-iso-store", data=None),
    ])


# -----------------------------------------------------------------------------
# 1. PREPARACIÓN DE DATOS
# -----------------------------------------------------------------------------
def _get_merged_data():
    co2 = df_capita.rename(columns={"Value": "CO2_pc"})[["ISOcode", "Country", "Year", "CO2_pc"]]
    gdp = df_gdp_capita.rename(columns={"Value": "GDP_pc"})[["ISOcode", "Year", "GDP_pc"]]
    co2_tot = df_totals.rename(columns={"Value": "CO2_total"})[["ISOcode", "Year", "CO2_total"]]

    df = pd.merge(co2, gdp, on=["ISOcode", "Year"], how="inner")
    df = pd.merge(df, co2_tot, on=["ISOcode", "Year"], how="inner")

    # Población aprox para tamaño burbuja
    df["Population"] = df["CO2_total"] / df["CO2_pc"]
    
    # Región
    df["Region"] = df["ISOcode"].map(ISO_TO_REGION).fillna("Other")

    df = df.dropna(subset=["CO2_pc", "GDP_pc"])
    # IMPORTANTE: Filtrar <= 0 para evitar errores en escalas logarítmicas
    df = df[(df["CO2_pc"] > 0) & (df["GDP_pc"] > 0)]
    
    return df


# -----------------------------------------------------------------------------
# 2. GRÁFICO PRINCIPAL: BURBUJAS
# -----------------------------------------------------------------------------
@callback(
    [Output("corr-bubble-graph", "figure"),
     Output("corr-value-display", "children"),
     Output("corr-explanation-display", "children")],
    Input("tabs", "active_tab"),
    Input("year-slider", "value"),
    Input("corr-selected-iso-store", "data")
)
def update_bubble_chart(active_tab, selected_year, selected_iso):
    if active_tab != "tab-3" or selected_year is None:
        return go.Figure(), "---", ""

    df = _get_merged_data()
    dff = df[df["Year"] == selected_year].copy()

    if dff.empty:
        return go.Figure().update_layout(title="No data"), "N/A", "No data"

    # --- CÁLCULO DE CORRELACIÓN (Sobre Logaritmos para ser realistas) ---
    corr = np.corrcoef(np.log10(dff["GDP_pc"]), np.log10(dff["CO2_pc"]))[0, 1]
    
    if corr > 0.7: text_expl = "Strong link: Richer = Dirtier"
    elif corr > 0.4: text_expl = "Moderate link"
    elif corr > 0: text_expl = "Weak link"
    else: text_expl = "Decoupled or Inverse!"

    # --- GRÁFICO ---
    # AQUÍ ESTÁ EL CAMBIO IMPORTANTE: custom_data=["ISOcode"]
    fig = px.scatter(
        dff,
        x="GDP_pc",
        y="CO2_pc",
        size="Population",    
        color="Region",       
        hover_name="Country",
        size_max=60,      
        template="plotly_white",
        log_x=True, 
        log_y=True,
        custom_data=["ISOcode"]  # <--- ESTO PERMITE SABER QUÉ PAÍS CLICAS
    )

    # Resaltar país seleccionado
    if selected_iso:
        selected = dff[dff["ISOcode"] == selected_iso]
        if not selected.empty:
            fig.add_trace(go.Scatter(
                x=selected["GDP_pc"],
                y=selected["CO2_pc"],
                mode='markers',
                marker=dict(size=20, color='rgba(0,0,0,0)', symbol='circle', line=dict(width=3, color='black')),
                showlegend=False,
                hoverinfo='skip'
            ))

    fig.update_layout(
        margin={"r": 20, "t": 30, "l": 20, "b": 20},
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"),
        xaxis_title="GDP per Capita (USD) [Log Scale]",
        yaxis_title="CO₂ per Capita (Tonnes) [Log Scale]",
    )

    return fig, f"{corr:.2f}", text_expl


# -----------------------------------------------------------------------------
# 3. GRÁFICO LATERAL: TRAYECTORIA (KUZNETS)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-trajectory-graph", "figure"),
    Input("tabs", "active_tab"),
    Input("corr-selected-iso-store", "data")
)
def update_trajectory(active_tab, selected_iso):
    if active_tab != "tab-3":
        return go.Figure()

    df = _get_merged_data()
    
    if not selected_iso:
        return go.Figure().update_layout(
            title="Click on a bubble to see history",
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{"text": "Select a country", "showarrow": False, "font": {"size": 14}}]
        )
    
    df_country = df[df["ISOcode"] == selected_iso].sort_values("Year")
    name = df_country["Country"].iloc[0] if not df_country.empty else selected_iso

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_country["GDP_pc"],
        y=df_country["CO2_pc"],
        mode="lines+markers",
        marker=dict(size=6, color=df_country["Year"], colorscale="Viridis", showscale=False),
        line=dict(color="#2c3e50", width=1.5),
        text=df_country["Year"],
        hovertemplate="<b>%{text}</b><br>GDP: $%{x:,.0f}<br>CO2: %{y:.2f}t<extra></extra>"
    ))

    if not df_country.empty:
        # Start
        fig.add_annotation(
            x=np.log10(df_country["GDP_pc"].iloc[0]), 
            y=np.log10(df_country["CO2_pc"].iloc[0]),
            text=str(df_country["Year"].iloc[0]), 
            showarrow=True, arrowhead=1, ax=20, ay=20, bgcolor="white"
        )
        # End
        fig.add_annotation(
            x=np.log10(df_country["GDP_pc"].iloc[-1]), 
            y=np.log10(df_country["CO2_pc"].iloc[-1]),
            text=str(df_country["Year"].iloc[-1]), 
            showarrow=True, arrowhead=1, ax=-20, ay=-20, bgcolor="white", font=dict(weight="bold")
        )

    fig.update_layout(
        title=f"Path: {name}",
        template="plotly_white",
        margin={"r": 10, "t": 40, "l": 10, "b": 10},
        xaxis=dict(title="GDP pc ($)", type="log"),
        yaxis=dict(title="CO2 pc (t)", type="log"),
        height=250
    )
    return fig


# -----------------------------------------------------------------------------
# 4. MODAL AVANZADO: DESACOPLE
# -----------------------------------------------------------------------------
@callback(
    Output("corr-modal-advanced", "is_open"),
    [Input("corr-open-advanced", "n_clicks"), Input("corr-close-advanced", "n_clicks")],
    [State("corr-modal-advanced", "is_open")],
)
def toggle_corr_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("corr-decoupling-graph", "figure"),
    Input("corr-modal-advanced", "is_open"),
    Input("year-slider", "value")
)
def update_decoupling_chart(is_open, selected_year):
    if not is_open or selected_year is None:
        return go.Figure()

    # 1. Definir año base de forma segura
    s_year = 2000 if min_year < 2000 else min_year
    if selected_year <= s_year:
        s_year = min_year
        if selected_year == s_year:
             return go.Figure().update_layout(title="Select a later year to see change")

    # 2. Agrupar y Sumar (para eliminar duplicados de ISOs)
    # Forzamos .astype(str) para que nadie se confunda con números/texto
    
    # CO2
    d_c_start = df_totals[df_totals["Year"] == s_year].copy()
    d_c_start["ISOcode"] = d_c_start["ISOcode"].astype(str)
    s_c_start = d_c_start.groupby("ISOcode")["Value"].sum()
    
    d_c_end = df_totals[df_totals["Year"] == selected_year].copy()
    d_c_end["ISOcode"] = d_c_end["ISOcode"].astype(str)
    s_c_end = d_c_end.groupby("ISOcode")["Value"].sum()

    # PIB
    d_g_start = df_gdp_total[df_gdp_total["Year"] == s_year].copy()
    d_g_start["ISOcode"] = d_g_start["ISOcode"].astype(str)
    s_g_start = d_g_start.groupby("ISOcode")["Value"].sum()
    
    d_g_end = df_gdp_total[df_gdp_total["Year"] == selected_year].copy()
    d_g_end["ISOcode"] = d_g_end["ISOcode"].astype(str)
    s_g_end = d_g_end.groupby("ISOcode")["Value"].sum()

    # 3. Fusión de datos (DataFrame con ISO en el índice)
    df_delta = pd.concat(
        [s_c_start, s_c_end, s_g_start, s_g_end], 
        axis=1, 
        keys=["CO2_s", "CO2_e", "GDP_s", "GDP_e"]
    ).dropna()

    if df_delta.empty:
        return go.Figure().update_layout(title="No shared data")

    # 4. Cálculos porcentuales
    # Evitamos dividir por cero
    df_delta = df_delta[(df_delta["CO2_s"] != 0) & (df_delta["GDP_s"] != 0)]
    
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100
    df_delta["dGDP"] = ((df_delta["GDP_e"] / df_delta["GDP_s"]) - 1) * 100
    
    # 5. RECUPERAR EL NOMBRE (TÉCNICA DEL DICCIONARIO - INFALIBLE)
    # Creamos un diccionario {ISO: Nombre} cogiendo el primer nombre que aparezca para cada ISO
    # Esto evita cualquier error de duplicados o índices.
    iso_map = df_totals.groupby("ISOcode")["Country"].first().to_dict()
    
    # "Mapeamos": Buscamos el nombre usando el índice (ISO)
    df_delta["Country"] = df_delta.index.map(iso_map)
    
    # Si algún país no tenía nombre en el diccionario (raro), rellenamos con su código ISO
    df_delta["Country"] = df_delta["Country"].fillna(df_delta.index.to_series())

    # Añadir Región
    df_delta["Region"] = df_delta.index.map(ISO_TO_REGION).fillna("Other")

    # 6. Filtros visuales (Quitar valores locos > 400%)
    df_delta = df_delta[(df_delta["dGDP"] < 400) & (df_delta["dGDP"] > -80)]
    df_delta = df_delta[(df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]

    # 7. Gráfico
    fig = px.scatter(
        df_delta, 
        x="dGDP", 
        y="dCO2", 
        color="Region",
        hover_name="Country", # <--- Ahora mostrará el nombre recuperado
        title=f"Decoupling Analysis: {s_year} vs {selected_year}",
        template="plotly_white", 
        height=450
    )
    
    # Líneas y zonas
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.add_vline(x=0, line_color="black", line_width=1)
    
    fig.add_shape(type="rect", x0=0, x1=400, y0=-100, y1=0, fillcolor="green", opacity=0.1, layer="below", line_width=0)
    fig.add_annotation(x=50, y=-20, text="<b>GREEN GROWTH</b>", showarrow=False, font=dict(color="green", size=14))

    fig.add_shape(type="rect", x0=0, x1=400, y0=0, y1=400, fillcolor="orange", opacity=0.1, layer="below", line_width=0)
    
    fig.update_xaxes(title="GDP Change (%)")
    fig.update_yaxes(title="CO2 Emissions Change (%)")

    return fig

# -----------------------------------------------------------------------------
# 5. ACTUALIZAR SELECCIÓN AL HACER CLICK (VERSIÓN CORREGIDA)
# -----------------------------------------------------------------------------
@callback(
    Output("corr-selected-iso-store", "data"),
    Input("corr-bubble-graph", "clickData"),
    Input("reset-global-btn", "n_clicks"),
    prevent_initial_call=False
)
def update_corr_country_store(clickData, _reset_clicks):
    if ctx.triggered_id == "reset-global-btn":
        return None
    if clickData and clickData.get("points"):
        # Recuperamos el ISOcode desde customdata
        try:
            return clickData["points"][0]["customdata"][0]
        except:
            return None
    return None