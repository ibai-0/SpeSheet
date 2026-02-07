import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table

# data
file_path = 'Data/CO2.xlsx'
meta_path = 'Data/country.csv'
gdp_path = 'Data/PIB.csv'
gdp_total_path = 'Data/PIB_total.csv'

COUNTRY_MERGE_MAP = {
    'Liechtenstein': 'Switzerland and Liechtenstein',
    'Switzerland': 'Switzerland and Liechtenstein',
    'Andorra': 'Spain and Andorra',
    'Spain': 'Spain and Andorra',
    'San Marino': 'Italy, San Marino and the Holy See',
    'Italy': 'Italy, San Marino and the Holy See',
    'Holy See': 'Italy, San Marino and the Holy See',
    'Monaco': 'France and Monaco',
    'France': 'France and Monaco',
    'Montenegro': 'Serbia and Montenegro',
    'Serbia': 'Serbia and Montenegro',
    'West Bank and Gaza': 'Israel and Palestine, State of',
    'Israel': 'Israel and Palestine, State of',
    'South Sudan': 'Sudan and South Sudan',
    'Sudan': 'Sudan and South Sudan'
}

ISO_MAP = {
    'Switzerland and Liechtenstein': 'CHE',
    'Spain and Andorra': 'ESP',
    'Italy, San Marino and the Holy See': 'ITA',
    'France and Monaco': 'FRA',
    'Serbia and Montenegro': 'SCG',
    'Israel and Palestine, State of': 'ISR',
    'Sudan and South Sudan': 'SDN'
}

VALID_REGIONS = {
    "East Asia & Pacific",
    "Europe & Central Asia",
    "Latin America & Caribbean",
    "Middle East & North Africa",
    "North America",
    "South Asia",
    "Sub-Saharan Africa",
}

xl = pd.ExcelFile(file_path)

def load_metadata_and_regions(meta_p: str):
    """
    Carga metadatos y devuelve:
    1. ISOs válidos (set)
    2. Diccionario ISO -> Región (para colorear gráficos)
    """
    try:
        meta = pd.read_csv(meta_p, dtype=str)
        meta.columns = [c.strip() for c in meta.columns]
        
        meta["Country Code"] = meta["Country Code"].fillna("").str.strip()
        meta["Region"] = meta["Region"].fillna("").str.strip()
        
        # Filtramos regiones oficiales
        real = meta[meta["Region"].isin(VALID_REGIONS)].copy()
        
        valid_isos = set(real["Country Code"])
        iso_region_map = dict(zip(real["Country Code"], real["Region"]))
        
        # --- AÑADIMOS MANUALMENTE LOS GRUPOS ESPECIALES ---
        for group_name, iso in ISO_MAP.items():
            valid_isos.add(iso)
            if iso not in iso_region_map:
                iso_region_map[iso] = "Europe & Central Asia" # Default si falta
        
        return valid_isos, iso_region_map
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return set(), {}

def safe_load_and_melt(keyword, id_vars):
    sheet_name = next((s for s in xl.sheet_names if keyword.lower() in s.lower()), None)
    if sheet_name:
        df = xl.parse(sheet_name)
        df.columns = [str(col) for col in df.columns]
        df_melted = df.melt(id_vars=id_vars, var_name='Year', value_name='Value')
        df_melted['Year'] = pd.to_numeric(df_melted['Year'], errors='coerce')
        df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')
        return df_melted.dropna(subset=['Year', 'Value'])
    return pd.DataFrame(columns=id_vars + ['Year', 'Value'])

def get_correlation_data():
    merged = pd.merge(
        df_totals, 
        df_capita, 
        on=['Country', 'ISOcode', 'Year'], 
        suffixes=('_total', '_capita')
    )

    merged = merged.rename(columns={
        'Value_total': 'Total_Emissions',
        'Value_capita': 'Per_Capita'
    })

    return merged

def get_cumulative_data():
    df = df_totals.sort_values(['Country', 'Year'])
    df['Cumulative_Value'] = df.groupby('Country')['Value'].cumsum()
    return df

def get_sector_summary(year):
    dff = df_sectors[df_sectors['Year'] == year]
    return dff.groupby('Sector')['Value'].sum().reset_index()

def load_gdp(csv_path: str):
    """
    Carga el CSV del World Bank (NY.GDP.PCAP.KD) y lo convierte a formato largo:
    Country, ISOcode, Year, Value
    """
    df_wide = pd.read_csv(csv_path, skiprows=4)
    df_wide.columns = [str(c).strip() for c in df_wide.columns]

    # columnas año: "1960", "1961", ...
    year_cols = [c for c in df_wide.columns if str(c).isdigit()]

    df_long = df_wide.melt(
        id_vars=["Country Name", "Country Code"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Value"
    ).rename(columns={
        "Country Name": "Country",
        "Country Code": "ISOcode"
    })

    df_long["Year"] = pd.to_numeric(df_long["Year"], errors="coerce")
    df_long["Value"] = pd.to_numeric(df_long["Value"], errors="coerce")
    df_long = df_long.dropna(subset=["Year", "Value"])

    # 1. Renombrar países individuales al nombre compuesto (Spain -> Spain and Andorra)
    df_long["Country"] = df_long["Country"].replace(COUNTRY_MERGE_MAP)

    # 2. Actualizar ISOs de esos grupos
    for group_name, iso in ISO_MAP.items():
        df_long.loc[df_long["Country"] == group_name, "ISOcode"] = iso

    # 3. SUMAR VALORES (Lo más importante: Spain + Andorra)
    df_long = df_long.groupby(["Country", "ISOcode", "Year"], as_index=False)["Value"].sum()

    # 4. Filtrar por rango de años y países reales
    if 'min_year' in globals():
        df_long = df_long[(df_long["Year"] >= min_year) & (df_long["Year"] <= max_year)]
    
    if 'REAL_COUNTRY_ISO3' in globals():
        df_long = df_long[df_long["ISOcode"].isin(REAL_COUNTRY_ISO3)]

    return df_long

## Data structure initialization
df_totals = safe_load_and_melt('totals', ['Country', 'ISOcode'])
df_capita = safe_load_and_melt('capita', ['Country', 'ISOcode'])
df_sectors = safe_load_and_melt('sector', ['Country', 'ISOcode', 'Sector'])
REAL_COUNTRY_ISO3, ISO_TO_REGION = load_metadata_and_regions(meta_path)

min_year = int(df_totals['Year'].min())
max_year = int(df_totals['Year'].max())

# Enriquecemos los dataframes con la columna 'Continent' para facilitar los gráficos por región
df_totals['Continent'] = df_totals['ISOcode'].map(ISO_TO_REGION)
df_capita['Continent'] = df_capita['ISOcode'].map(ISO_TO_REGION)
df_sectors['Continent'] = df_sectors['ISOcode'].map(ISO_TO_REGION)

# Filtramos solo países reales (para quitar regiones agregadas si las hubiera en el Excel)
df_totals = df_totals[df_totals['ISOcode'].isin(REAL_COUNTRY_ISO3)]
df_capita = df_capita[df_capita['ISOcode'].isin(REAL_COUNTRY_ISO3)]
df_sectors = df_sectors[df_sectors['ISOcode'].isin(REAL_COUNTRY_ISO3)]

df_gdp_capita = load_gdp(gdp_path)
df_gdp_total = load_gdp(gdp_total_path)
df_correlation = get_correlation_data()
df_cumulative = get_cumulative_data()

# --- Life Expectancy Data ---
def load_life_expectancy():
    """Carga y procesa el archivo LIFE_EXPECTANCY.csv"""
    try:
        # El CSV tiene un formato especial: cada línea completa está entre comillas
        # y los valores internos usan comillas dobles escapadas
        # Formato: "valor1,""valor2"",""valor3"",..."
        
        rows = []
        with open('Data/LIFE_EXPECTANCY.csv', 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 4:  # Saltar metadata
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                # Remover la comilla inicial y final de toda la línea
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                
                # Ahora parsear considerando que los valores están con ""
                # Dividir por ,"" que es el separador entre campos
                parts = []
                current = ""
                i = 0
                while i < len(line):
                    if i < len(line) - 2 and line[i:i+3] == ',""':
                        # Fin de un campo, inicio de otro
                        parts.append(current)
                        current = ""
                        i += 3
                    elif i < len(line) - 1 and line[i:i+2] == '""':
                        # Comillas dobles dentro de un valor - ignorar
                        i += 2
                    else:
                        current += line[i]
                        i += 1
                
                # Agregar el último campo
                if current:
                    parts.append(current)
                
                # Filtrar campos vacíos o con solo puntos y comas
                parts = [p for p in parts if p and not p.startswith(';;;;')]
                
                if parts and len(parts) > 2:
                    rows.append(parts)
        
        if len(rows) < 2:
            raise ValueError(f"Solo {len(rows)} filas leídas")
        
        # Primera fila = headers
        headers = rows[0]
        data_rows = rows[1:]
        
        # Ajustar filas para que todas tengan el mismo número de columnas
        max_cols = len(headers)
        for row in data_rows:
            while len(row) < max_cols:
                row.append('')
            if len(row) > max_cols:
                row[:] = row[:max_cols]
        
        # Crear dataframe
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Renombrar primeras columnas
        cols = df.columns.tolist()
        df = df.rename(columns={cols[0]: 'Country', cols[1]: 'ISOcode'})
        
        # Buscar columnas de años
        year_cols = [col for col in df.columns if col.isdigit() and len(col) == 4]
        
        if not year_cols:
            raise ValueError("No se encontraron columnas de años")
        
        # Filtrar solo Country, ISOcode y años
        df = df[['Country', 'ISOcode'] + year_cols]
        
        # Convertir a formato long
        df_melted = df.melt(
            id_vars=['Country', 'ISOcode'],
            var_name='Year',
            value_name='Life_Expectancy'
        )
        
        # Convertir tipos
        df_melted['Year'] = pd.to_numeric(df_melted['Year'], errors='coerce')
        df_melted['Life_Expectancy'] = pd.to_numeric(df_melted['Life_Expectancy'], errors='coerce')
        df_melted['ISOcode'] = df_melted['ISOcode'].str.strip()
        
        # Eliminar nulos
        df_melted = df_melted.dropna(subset=['Year', 'Life_Expectancy'])
        
        # --- APLICAR MERGE DE PAÍSES (igual que GDP) ---
        # 1. Renombrar países individuales al nombre compuesto
        df_melted["Country"] = df_melted["Country"].replace(COUNTRY_MERGE_MAP)
        
        # 2. Actualizar ISOs de esos grupos
        for group_name, iso in ISO_MAP.items():
            df_melted.loc[df_melted["Country"] == group_name, "ISOcode"] = iso
        
        # 3. PROMEDIAR VALORES de esperanza de vida para países agrupados
        # (usamos promedio ponderado o simple promedio)
        df_melted = df_melted.groupby(["Country", "ISOcode", "Year"], as_index=False)["Life_Expectancy"].mean()
        
        return df_melted
        
    except Exception as e:
        print(f"Error loading life expectancy data: {e}")
        return pd.DataFrame(columns=['Country', 'ISOcode', 'Year', 'Life_Expectancy'])

# Cargar datos de esperanza de vida
df_life_expectancy = load_life_expectancy()   

# --- Helper precomputed merges for UI convenience ---

def get_merged_for_correlation():
    """Return merged DataFrame with CO2 per capita, GDP per capita and totals.

    Columns: ISOcode, Country, Year, CO2_pc, GDP_pc, CO2_total, Population, Region
    """
    co2 = df_capita.rename(columns={"Value": "CO2_pc"})[["ISOcode", "Country", "Year", "CO2_pc"]]
    gdp = df_gdp_capita.rename(columns={"Value": "GDP_pc"})[["ISOcode", "Year", "GDP_pc"]]
    co2_tot = df_totals.rename(columns={"Value": "CO2_total"})[["ISOcode", "Year", "CO2_total"]]

    df = pd.merge(co2, gdp, on=["ISOcode", "Year"], how="inner")
    df = pd.merge(df, co2_tot, on=["ISOcode", "Year"], how="inner")

    # Estimate population (proxy) and region mapping
    df["Population"] = df["CO2_total"] / df["CO2_pc"]
    df["Region"] = df["ISOcode"].map(ISO_TO_REGION).fillna("Other")

    df = df.dropna(subset=["CO2_pc", "GDP_pc"]).copy()
    df = df[(df["CO2_pc"] > 0) & (df["GDP_pc"] > 0)]
    return df


def get_merged_life_progress():
    """Return merged DataFrame combining CO2 (capita & totals) with Life Expectancy.

    Columns include: ISOcode, Country, Year, Value_capita, Value_total, Population_Proxy,
    Life_Expectancy, Continente
    """
    # Prepare sources
    dff_capita = df_capita[["ISOcode", "Country", "Year", "Value"]].copy()
    dff_totals = df_totals[["ISOcode", "Year", "Value"]].copy()
    dff_life = df_life_expectancy[["ISOcode", "Country", "Year", "Life_Expectancy"]].copy()

    # Clean ISOcodes
    for d in (dff_capita, dff_totals, dff_life):
        d["ISOcode"] = d["ISOcode"].astype(str).str.strip().str.replace('"', '')

    # Merge CO2 capita with totals on ISOcode+Year
    df_co2_combined = pd.merge(
        dff_capita.rename(columns={"Value": "Value_capita"}),
        dff_totals.rename(columns={"Value": "Value_total"}),
        on=["ISOcode", "Year"],
        how="inner",
    )

    # Population proxy
    df_co2_combined["Population_Proxy"] = df_co2_combined.apply(
        lambda r: (r["Value_total"] / r["Value_capita"]) if r["Value_capita"] and r["Value_capita"] > 0 else 1,
        axis=1
    )

    # Merge with life expectancy
    df_merged = pd.merge(
        df_co2_combined,
        dff_life,
        on=["ISOcode", "Year"],
        how="inner",
        suffixes=("_co2", "_life")
    )

    # Use CO2 country name where available
    if "Country_co2" in df_merged.columns:
        df_merged["Country"] = df_merged["Country_co2"]

    # Map to World Bank region using ISO_TO_REGION
    df_merged["Region"] = df_merged["ISOcode"].map(ISO_TO_REGION).fillna("Other")

    # Keep only useful columns
    keep = ["ISOcode", "Country", "Year", "Value_capita", "Value_total", "Population_Proxy", "Life_Expectancy", "Region"]
    existing = [c for c in keep if c in df_merged.columns]
    df_merged = df_merged[existing].copy()

    # Filter obviously invalid values
    if "Value_capita" in df_merged.columns:
        df_merged = df_merged[df_merged["Value_capita"] > 0]
    if "Life_Expectancy" in df_merged.columns:
        df_merged = df_merged[df_merged["Life_Expectancy"] > 0]

    return df_merged

# =============================================================================
# Tab 2 helpers (GDP & Life Expectancy tab)
# =============================================================================
# NOTE: These helpers exist to keep tab2.py callbacks small and to avoid repeating
# expensive groupby/filters on every interaction. They are *only* used by Tab 2.

TAB2_SMALL_COUNTRY_ISOS = {'AND', 'MCO', 'LIE', 'SMR', 'VAT', 'MNE', 'PSE', 'SSD'}

# Precomputed global averages (used in Tab 2 line charts)
TAB2_GDP_TOTAL_AVG_BY_YEAR = (
    df_gdp_total.dropna(subset=["Value"])
    .groupby("Year", as_index=False)["Value"]
    .mean()
)

TAB2_GDP_CAPITA_AVG_BY_YEAR = (
    df_gdp_capita.dropna(subset=["Value"])
    .groupby("Year", as_index=False)["Value"]
    .mean()
)

TAB2_LIFE_AVG_BY_YEAR = (
    df_life_expectancy.dropna(subset=["Life_Expectancy"])
    .groupby("Year", as_index=False)["Life_Expectancy"]
    .mean()
)

# Precomputed continental progress series (used in Tab 2 'Continental Progress')
TAB2_LIFE_CONTINENT_AVG = (
    df_life_expectancy.dropna(subset=["Life_Expectancy"])
    .assign(Continent=lambda d: d["ISOcode"].map(ISO_TO_REGION).fillna("Other"))
    .query("Continent != 'Other'")
    .groupby(["Year", "Continent"], as_index=False)["Life_Expectancy"]
    .mean()
)

# Fixed color mapping (kept here so Tab 2 stays compact)
TAB2_LIFE_CONTINENT_COLOR_MAP = {
    'Europe & Central Asia': '#3498db',       # Blue
    'East Asia & Pacific': '#e74c3c',         # Red
    'South Asia': '#9b59b6',                  # Purple
    'North America': '#2ecc71',               # Green
    'Latin America & Caribbean': '#1abc9c',   # Teal
    'Middle East & North Africa': '#f39c12',  # Orange
    'Sub-Saharan Africa': '#f1c40f',          # Yellow
}

def tab2_get_gdp_year_df(year: int, view: str):
    """Return GDP dataframe filtered to a given year.

    Args:
        year: Selected year from the slider.
        view: "total" or "capita".
    """
    base = df_gdp_total if view == "total" else df_gdp_capita
    return base[base["Year"] == year].dropna(subset=["Value"]).copy()

def tab2_get_gdp_map_df(year: int, view: str):
    """Return GDP dataframe ready for the choropleth (includes log10 color)."""
    dff = tab2_get_gdp_year_df(year, view)
    dff = dff[dff["Value"] > 0].copy()
    if not dff.empty:
        dff["ColorValue"] = np.log10(dff["Value"])
    return dff

def tab2_get_life_year_df(year: int, filter_small_isos: bool = True):
    """Return life expectancy dataframe filtered to a given year."""
    dff = df_life_expectancy[df_life_expectancy["Year"] == year].dropna(subset=["Life_Expectancy"]).copy()
    if filter_small_isos:
        dff = dff[~dff["ISOcode"].isin(TAB2_SMALL_COUNTRY_ISOS)]
    return dff

def tab2_get_default_iso_gdp(year: int):
    """Fallback ISO: country with max GDP (total) for the given year."""
    dff = df_gdp_total[df_gdp_total["Year"] == year].dropna(subset=["Value"])
    if dff.empty:
        return None
    return dff.loc[dff["Value"].idxmax(), "ISOcode"]

def tab2_get_default_iso_life(year: int):
    """Fallback ISO: country with max life expectancy for the given year."""
    dff = tab2_get_life_year_df(year, filter_small_isos=False)
    if dff.empty:
        return None
    return dff.loc[dff["Life_Expectancy"].idxmax(), "ISOcode"]

def tab2_get_gdp_country_series(iso: str):
    """Return (total_series, capita_series, country_name) for a given ISO."""
    iso = str(iso).strip().replace('"', '')
    c_total = df_gdp_total[df_gdp_total["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    c_cap = df_gdp_capita[df_gdp_capita["ISOcode"] == iso].dropna(subset=["Value"]).copy()
    name = None
    if not c_total.empty:
        name = c_total["Country"].iloc[0]
    elif not c_cap.empty:
        name = c_cap["Country"].iloc[0]
    return c_total, c_cap, name

def tab2_get_life_country_series(iso: str):
    """Return life expectancy series for a given ISO."""
    iso = str(iso).strip().replace('"', '')
    return df_life_expectancy[df_life_expectancy["ISOcode"] == iso].dropna(subset=["Life_Expectancy"]).copy()


# =============================================================================
# Tab 3 helpers (Correlation / Decoupling tab)
# =============================================================================
# NOTE: These helpers exist to keep tab3.py callbacks small and to avoid repeating
# heavy joins / aggregations on every interaction. They are *only* used by Tab 3.


# Fixed region color mapping used by the Life Expectancy bubble chart.
TAB3_LIFE_REGION_COLOR_MAP = {
    'Europe & Central Asia': '#3498db',
    'East Asia & Pacific': '#e74c3c',
    'South Asia': '#f39c12',
    'Middle East & North Africa': '#9b59b6',
    'North America': '#2ecc71',
    'Latin America & Caribbean': '#1abc9c',
    'Sub-Saharan Africa': '#e67e22',
    'Other': '#95a5a6'
}


def tab3_get_gdp_bubble_year_df(year: int) -> pd.DataFrame:
    """Return the pre-merged GDP/CO2-per-capita dataframe filtered to one year."""
    df = get_merged_for_correlation()
    return df[df["Year"] == year].copy()


def tab3_get_life_bubble_year_df(year: int) -> pd.DataFrame:
    """Return the pre-merged Life/CO2-per-capita dataframe filtered to one year."""
    df = get_merged_life_progress()
    return df[df["Year"] == year].copy()


def tab3_get_gdp_country_trajectory_df(iso: str) -> pd.DataFrame:
    """Return the historical trajectory (all years) for a country in GDP view."""
    iso = str(iso).strip().replace('"', '')
    df = get_merged_for_correlation()
    df_c = df[df["ISOcode"] == iso].sort_values("Year").copy()
    # Defensive filters for log scales
    return df_c[(df_c["GDP_pc"] > 0) & (df_c["CO2_pc"] > 0)]


def tab3_get_life_country_trajectory_df(iso: str) -> pd.DataFrame:
    """Return the historical trajectory (all years) for a country in Life view."""
    iso = str(iso).strip().replace('"', '')
    df = get_merged_life_progress()
    df_c = df[df["ISOcode"] == iso].sort_values("Year").copy()
    # Defensive filters for log scales / invalid life expectancy
    return df_c[(df_c["Value_capita"] > 0) & (df_c["Life_Expectancy"] > 0)]


def _tab3_aggregate_iso(df: pd.DataFrame, year: int, value_col: str, agg: str) -> pd.Series:
    """Aggregate a dataframe by ISO for a given year.

    Args:
        df: Source dataframe containing ISOcode, Year and the value column.
        year: Year to filter.
        value_col: Column to aggregate.
        agg: "sum" or "mean".
    """
    d = df[df["Year"] == year].copy()
    d["ISOcode"] = d["ISOcode"].astype(str).str.strip().str.replace('"', '')
    grouped = d.groupby("ISOcode")[value_col]
    return grouped.mean() if agg == "mean" else grouped.sum()


def _tab3_attach_country_region(df_delta: pd.DataFrame, source_df: pd.DataFrame) -> pd.DataFrame:
    """Attach Country name and Region to a delta dataframe indexed by ISO."""
    iso_to_country = source_df.groupby("ISOcode")["Country"].first().to_dict()
    df_delta["Country"] = df_delta.index.map(lambda x: iso_to_country.get(x, x))
    df_delta["Region"] = df_delta.index.map(ISO_TO_REGION).fillna("Other")
    return df_delta


def tab3_get_decoupling_delta(selected_year: int, start_year: int = 1970):
    """Build the decoupling delta dataframe for Tab 3 (GDP total vs CO2 total).

    Returns None when selected_year <= start_year.
    """
    if selected_year <= start_year:
        return None

    co2_s = _tab3_aggregate_iso(df_totals, start_year, "Value", "sum")
    co2_e = _tab3_aggregate_iso(df_totals, selected_year, "Value", "sum")
    gdp_s = _tab3_aggregate_iso(df_gdp_total, start_year, "Value", "sum")
    gdp_e = _tab3_aggregate_iso(df_gdp_total, selected_year, "Value", "sum")

    df_delta = pd.concat(
        [co2_s, co2_e, gdp_s, gdp_e],
        axis=1,
        keys=["CO2_s", "CO2_e", "GDP_s", "GDP_e"],
    ).dropna()

    if df_delta.empty:
        return df_delta

    df_delta = df_delta[(df_delta["CO2_s"] != 0) & (df_delta["GDP_s"] != 0)]
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100
    df_delta["dGDP"] = ((df_delta["GDP_e"] / df_delta["GDP_s"]) - 1) * 100

    df_delta = _tab3_attach_country_region(df_delta, df_totals)

    # Visual filters (same thresholds as the original tab3.py)
    df_delta = df_delta[(df_delta["dGDP"] < 400) & (df_delta["dGDP"] > -80) &
                        (df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]

    return df_delta


def tab3_get_life_progress_delta(selected_year: int, start_year: int = 1970):
    """Build the life progress delta dataframe for Tab 3 (Life vs CO2 per-capita).

    Returns None when selected_year <= start_year.
    """
    if selected_year <= start_year:
        return None

    life_s = _tab3_aggregate_iso(df_life_expectancy, start_year, "Life_Expectancy", "mean")
    life_e = _tab3_aggregate_iso(df_life_expectancy, selected_year, "Life_Expectancy", "mean")
    co2_s = _tab3_aggregate_iso(df_capita, start_year, "Value", "sum")
    co2_e = _tab3_aggregate_iso(df_capita, selected_year, "Value", "sum")

    df_delta = pd.concat(
        [life_s, life_e, co2_s, co2_e],
        axis=1,
        keys=["Life_s", "Life_e", "CO2_s", "CO2_e"],
    ).dropna()

    if df_delta.empty:
        return df_delta

    df_delta["dLife"] = df_delta["Life_e"] - df_delta["Life_s"]
    df_delta = df_delta[df_delta["CO2_s"] != 0]
    df_delta["dCO2"] = ((df_delta["CO2_e"] / df_delta["CO2_s"]) - 1) * 100

    df_delta = _tab3_attach_country_region(df_delta, df_capita)

    # Visual filters (same thresholds as the original tab3.py)
    df_delta = df_delta[(df_delta["dLife"] > -20) & (df_delta["dLife"] < 40) &
                        (df_delta["dCO2"] < 400) & (df_delta["dCO2"] > -80)]

    # Sustainability score (used for top/bottom ranking blocks)
    df_delta["Sustainability_Score"] = df_delta["dLife"] - (df_delta["dCO2"] / 10)

    return df_delta
