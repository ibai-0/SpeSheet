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

min_year = int(df_totals['Year'].min())
max_year = int(df_totals['Year'].max())

REAL_COUNTRY_ISO3, ISO_TO_REGION = load_metadata_and_regions(meta_path)

df_gdp_capita = load_gdp(gdp_path)
df_gdp_total = load_gdp(gdp_total_path)
df_correlation = get_correlation_data()
df_cumulative = get_cumulative_data()

# --- ENGLISH CONTINENT MAPPING ---
continent_map = {
    # Africa
    'Algeria': 'Africa', 'Angola': 'Africa', 'Benin': 'Africa', 'Botswana': 'Africa', 'Burkina Faso': 'Africa', 
    'Burundi': 'Africa', 'Cameroon': 'Africa', 'Cape Verde': 'Africa', 'Central African Republic': 'Africa', 
    'Chad': 'Africa', 'Comoros': 'Africa', 'Congo': 'Africa', 'Democratic Republic of Congo': 'Africa', 
    'Djibouti': 'Africa', 'Egypt': 'Africa', 'Equatorial Guinea': 'Africa', 'Eritrea': 'Africa', 
    'Ethiopia': 'Africa', 'Gabon': 'Africa', 'Gambia': 'Africa', 'Ghana': 'Africa', 'Guinea': 'Africa', 
    'Guinea-Bissau': 'Africa', 'Ivory Coast': 'Africa', 'Kenya': 'Africa', 'Lesotho': 'Africa', 
    'Liberia': 'Africa', 'Libya': 'Africa', 'Madagascar': 'Africa', 'Malawi': 'Africa', 'Mali': 'Africa', 
    'Mauritania': 'Africa', 'Mauritius': 'Africa', 'Morocco': 'Africa', 'Mozambique': 'Africa', 
    'Namibia': 'Africa', 'Niger': 'Africa', 'Nigeria': 'Africa', 'Rwanda': 'Africa', 
    'Sao Tome and Principe': 'Africa', 'Senegal': 'Africa', 'Seychelles': 'Africa', 'Sierra Leone': 'Africa', 
    'Somalia': 'Africa', 'South Africa': 'Africa', 'South Sudan': 'Africa', 'Sudan': 'Africa', 
    'Swaziland': 'Africa', 'Tanzania': 'Africa', 'Togo': 'Africa', 'Tunisia': 'Africa', 'Uganda': 'Africa', 
    'Zambia': 'Africa', 'Zimbabwe': 'Africa',
    
    # Asia
    'Afghanistan': 'Asia', 'Armenia': 'Asia', 'Azerbaijan': 'Asia', 'Bahrain': 'Asia', 'Bangladesh': 'Asia', 
    'Bhutan': 'Asia', 'Brunei': 'Asia', 'Cambodia': 'Asia', 'China': 'Asia', 'Cyprus': 'Asia', 
    'Georgia': 'Asia', 'India': 'Asia', 'Indonesia': 'Asia', 'Iran': 'Asia', 'Iraq': 'Asia', 
    'Israel': 'Asia', 'Japan': 'Asia', 'Jordan': 'Asia', 'Kazakhstan': 'Asia', 'Kuwait': 'Asia', 
    'Kyrgyzstan': 'Asia', 'Laos': 'Asia', 'Lebanon': 'Asia', 'Malaysia': 'Asia', 'Maldives': 'Asia', 
    'Mongolia': 'Asia', 'Myanmar': 'Asia', 'Nepal': 'Asia', 'North Korea': 'Asia', 'Oman': 'Asia', 
    'Pakistan': 'Asia', 'Palestine': 'Asia', 'Philippines': 'Asia', 'Qatar': 'Asia', 'Saudi Arabia': 'Asia', 
    'Singapore': 'Asia', 'South Korea': 'Asia', 'Sri Lanka': 'Asia', 'Syria': 'Asia', 'Taiwan': 'Asia', 
    'Tajikistan': 'Asia', 'Thailand': 'Asia', 'Timor': 'Asia', 'Turkey': 'Asia', 'Turkmenistan': 'Asia', 
    'United Arab Emirates': 'Asia', 'Uzbekistan': 'Asia', 'Vietnam': 'Asia', 'Yemen': 'Asia',
    
    # Europe
    'Albania': 'Europe', 'Andorra': 'Europe', 'Austria': 'Europe', 'Belarus': 'Europe', 'Belgium': 'Europe', 
    'Bosnia and Herzegovina': 'Europe', 'Bulgaria': 'Europe', 'Croatia': 'Europe', 'Czech Republic': 'Europe', 
    'Denmark': 'Europe', 'Estonia': 'Europe', 'Finland': 'Europe', 'France': 'Europe', 'Germany': 'Europe', 
    'Greece': 'Europe', 'Hungary': 'Europe', 'Iceland': 'Europe', 'Ireland': 'Europe', 'Italy': 'Europe', 
    'Latvia': 'Europe', 'Liechtenstein': 'Europe', 'Lithuania': 'Europe', 'Luxembourg': 'Europe', 
    'Malta': 'Europe', 'Moldova': 'Europe', 'Monaco': 'Europe', 'Montenegro': 'Europe', 'Netherlands': 'Europe', 
    'North Macedonia': 'Europe', 'Norway': 'Europe', 'Poland': 'Europe', 'Portugal': 'Europe', 
    'Romania': 'Europe', 'Russia': 'Europe', 'San Marino': 'Europe', 'Serbia': 'Europe', 'Slovakia': 'Europe', 
    'Slovenia': 'Europe', 'Spain': 'Europe', 'Sweden': 'Europe', 'Switzerland': 'Europe', 'Ukraine': 'Europe', 
    'United Kingdom': 'Europe',
    
    # Americas
    'Antigua and Barbuda': 'Americas', 'Bahamas': 'Americas', 'Barbados': 'Americas', 'Belize': 'Americas', 
    'Canada': 'Americas', 'Costa Rica': 'Americas', 'Cuba': 'Americas', 'Dominica': 'Americas', 
    'Dominican Republic': 'Americas', 'El Salvador': 'Americas', 'Grenada': 'Americas', 'Guatemala': 'Americas', 
    'Haiti': 'Americas', 'Honduras': 'Americas', 'Jamaica': 'Americas', 'Mexico': 'Americas', 
    'Nicaragua': 'Americas', 'Panama': 'Americas', 'Saint Kitts and Nevis': 'Americas', 'Saint Lucia': 'Americas', 
    'Saint Vincent and the Grenadines': 'Americas', 'Trinidad and Tobago': 'Americas', 'USA': 'Americas', 
    'United States': 'Americas', 'Argentina': 'Americas', 'Bolivia': 'Americas', 'Brazil': 'Americas', 
    'Chile': 'Americas', 'Colombia': 'Americas', 'Ecuador': 'Americas', 'Guyana': 'Americas', 
    'Paraguay': 'Americas', 'Peru': 'Americas', 'Suriname': 'Americas', 'Uruguay': 'Americas', 
    'Venezuela': 'Americas',
    
    # Oceania
    'Australia': 'Oceania', 'Fiji': 'Oceania', 'Kiribati': 'Oceania', 'Marshall Islands': 'Oceania', 
    'Micronesia': 'Oceania', 'Nauru': 'Oceania', 'New Zealand': 'Oceania', 'Palau': 'Oceania', 
    'Papua New Guinea': 'Oceania', 'Samoa': 'Oceania', 'Solomon Islands': 'Oceania', 'Tonga': 'Oceania', 
    'Tuvalu': 'Oceania', 'Vanuatu': 'Oceania',

    'Spain and Andorra': 'Europe',
    'Switzerland and Liechtenstein': 'Europe',
    'Italy, San Marino and the Holy See': 'Europe',
    'France and Monaco': 'Europe',
    'Serbia and Montenegro': 'Europe',
    'Israel and Palestine, State of': 'Asia',
    'Sudan and South Sudan': 'Africa',
    'Myanmar/Burma': 'Asia',
    'Czechia': 'Europe',
    'Hong Kong': 'Asia',
    'Curacao': 'Americas',
    'Côte d’Ivoire': 'Africa',
    'Democratic Republic of the Congo': 'Africa',
    'New Caledonia': 'Oceania',
    'Guadeloupe': 'Americas',
    'French Polynesia': 'Oceania',
    'Réunion': 'Africa',
    'Macao': 'Asia',
    'The Gambia': 'Africa',
    'Martinique': 'Americas',
    'French Guiana': 'Americas',
    'Saint Pierre and Miquelon': 'Americas',
    'Cabo Verde': 'Africa',
    'Bermuda': 'Americas',
    'British Virgin Islands': 'Americas',
    'Cayman Islands': 'Americas',
    'Western Sahara': 'Africa',
    'Puerto Rico': 'Americas',
    'Cook Islands': 'Oceania',
    'Eswatini': 'Africa',
    'Gibraltar': 'Europe',
    'Aruba': 'Americas',
    'Falkland Islands': 'Americas',
    'São Tomé and Príncipe': 'Africa',
    'Turks and Caicos Islands': 'Americas',
    'Timor-Leste': 'Asia',
    'Greenland': 'Americas'
}

# Apply to the global DataFrame
df_totals['Continent'] = df_totals['Country'].map(continent_map).fillna('Others')