import pandas as pd
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