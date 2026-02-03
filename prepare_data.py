import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table

# data
file_path = 'Data/CO2.xlsx'
xl = pd.ExcelFile(file_path)

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

    df_long["ISOcode"] = df_long["ISOcode"].astype(str).str.strip()
    df_long["Year"] = pd.to_numeric(df_long["Year"], errors="coerce")
    df_long["Value"] = pd.to_numeric(df_long["Value"], errors="coerce")
    
    df_long = df_long.dropna(subset=["Year"])
    df_long = df_long[(df_long["Year"] >= min_year) & (df_long["Year"] <= max_year)]

    df_long = df_long[df_long["ISOcode"].isin(REAL_COUNTRY_ISO3)]

    return df_long

VALID_REGIONS = {
    "East Asia & Pacific",
    "Europe & Central Asia",
    "Latin America & Caribbean",
    "Middle East & North Africa",
    "North America",
    "South Asia",
    "Sub-Saharan Africa",
}

def load_real_countries_from_metadata(meta_path: str):
    meta = pd.read_csv(meta_path, dtype=str)
    meta.columns = [c.strip() for c in meta.columns]

    # Normaliza
    meta["Country Code"] = meta["Country Code"].fillna("").str.strip()
    meta["Region"] = meta["Region"].fillna("").str.strip()

    # ✅ SOLO países reales: región en las 7 regiones oficiales (excluye Aggregates, vacíos, etc.)
    real = meta.loc[meta["Region"].isin(VALID_REGIONS), "Country Code"]

    # ISO3 de 3 letras
    real = real[real.str.len() == 3]
    return set(real)

## Data structure initialization
df_totals = safe_load_and_melt('totals', ['Country', 'ISOcode'])
df_capita = safe_load_and_melt('capita', ['Country', 'ISOcode'])
df_sectors = safe_load_and_melt('sector', ['Country', 'ISOcode', 'Sector'])

min_year = int(df_totals['Year'].min())
max_year = int(df_totals['Year'].max())

REAL_COUNTRY_ISO3 = load_real_countries_from_metadata("country.csv")

## GDP Data.
df_gdp_capita = load_gdp("Data/PIB.csv")
df_gdp_total = load_gdp("Data/PIB_total.csv")
df_correlation = get_correlation_data()
df_cumulative = get_cumulative_data()