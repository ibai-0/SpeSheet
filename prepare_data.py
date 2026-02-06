import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table

file_path = 'Data/CO2.xlsx'
meta_path = 'Data/country.csv'
gdp_path = 'Data/PIB.csv'
gdp_total_path = 'Data/PIB_total.csv'

# Merge small ISO codes into main countries
ISO_CODE_MERGE_MAP = {
    'LIE': 'CHE',
    'AND': 'ESP',
    'SMR': 'ITA',
    'VAT': 'ITA',
    'MCO': 'FRA',
    'MNE': 'SRB',
    'PSE': 'ISR',
    'SSD': 'SDN'
}

# ISO codes for small countries excluded after the merge
EXCLUDED_SMALL_COUNTRY_ISOS = {
    'LIE',
    'AND',
    'SMR',
    'VAT',
    'MCO',
    'MNE',
    'PSE',
    'SSD'
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
    Load metadata and return:
    1. Valid ISO codes (set)
    2. ISO -> Region map (for chart colors)
    3. ISO -> Country map (English name)
    """
    try:
        meta = pd.read_csv(meta_p, dtype=str)
        meta.columns = [c.strip() for c in meta.columns]
        
        meta["Country Code"] = meta["Country Code"].fillna("").str.strip()
        meta["Region"] = meta["Region"].fillna("").str.strip()
        
        real = meta[meta["Region"].isin(VALID_REGIONS)].copy()
        
        valid_isos = set(real["Country Code"])
        iso_region_map = dict(zip(real["Country Code"], real["Region"]))
        iso_country_map = dict(zip(real["Country Code"], real["TableName"]))
        
        return valid_isos, iso_region_map, iso_country_map
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return set(), {}, {}

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
    Load the World Bank CSV (NY.GDP.PCAP.KD) and convert it to long format:
    Country, ISOcode, Year, Value
    """
    df_wide = pd.read_csv(csv_path, skiprows=4)
    df_wide.columns = [str(c).strip() for c in df_wide.columns]

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

    df_long["ISOcode"] = df_long["ISOcode"].replace(ISO_CODE_MERGE_MAP)

    df_long = df_long.groupby(["ISOcode", "Year"], as_index=False)["Value"].sum()

    df_wide_clean = pd.read_csv(csv_path, skiprows=4)
    country_map = dict(zip(df_wide_clean["Country Code"].str.strip(), df_wide_clean["Country Name"]))
    df_long["Country"] = df_long["ISOcode"].map(country_map)

    df_long = df_long[~df_long["ISOcode"].isin(EXCLUDED_SMALL_COUNTRY_ISOS)]

    if 'min_year' in globals():
        df_long = df_long[(df_long["Year"] >= min_year) & (df_long["Year"] <= max_year)]
    
    if 'REAL_COUNTRY_ISO3' in globals():
        df_long = df_long[df_long["ISOcode"].isin(REAL_COUNTRY_ISO3)]

    return df_long

df_totals = safe_load_and_melt('totals', ['Country', 'ISOcode'])
df_capita = safe_load_and_melt('capita', ['Country', 'ISOcode'])
df_sectors = safe_load_and_melt('sector', ['Country', 'ISOcode', 'Sector'])
REAL_COUNTRY_ISO3, ISO_TO_REGION, ISO_TO_COUNTRY = load_metadata_and_regions(meta_path)

min_year = int(df_totals['Year'].min())
max_year = int(df_totals['Year'].max())

df_totals['Continent'] = df_totals['ISOcode'].map(ISO_TO_REGION)
df_capita['Continent'] = df_capita['ISOcode'].map(ISO_TO_REGION)
df_sectors['Continent'] = df_sectors['ISOcode'].map(ISO_TO_REGION)

df_totals = df_totals[df_totals['ISOcode'].isin(REAL_COUNTRY_ISO3)]
df_capita = df_capita[df_capita['ISOcode'].isin(REAL_COUNTRY_ISO3)]
df_sectors = df_sectors[df_sectors['ISOcode'].isin(REAL_COUNTRY_ISO3)]

def _apply_country_names(df):
    if "ISOcode" not in df.columns or "Country" not in df.columns:
        return df
    df = df.copy()
    df["Country"] = df["ISOcode"].map(ISO_TO_COUNTRY).fillna(df["Country"])
    return df

df_totals = _apply_country_names(df_totals)
df_capita = _apply_country_names(df_capita)
df_sectors = _apply_country_names(df_sectors)

df_gdp_capita = _apply_country_names(load_gdp(gdp_path))
df_gdp_total = _apply_country_names(load_gdp(gdp_total_path))
df_correlation = get_correlation_data()
df_cumulative = get_cumulative_data()

def load_life_expectancy():
    """Load and process LIFE_EXPECTANCY.csv"""
    try:
        # Custom parser for quoted lines and escaped quotes
        
        rows = []
        with open('Data/LIFE_EXPECTANCY.csv', 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 4:
                    continue
                
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                
                parts = []
                current = ""
                i = 0
                while i < len(line):
                    if i < len(line) - 2 and line[i:i+3] == ',""':
                        parts.append(current)
                        current = ""
                        i += 3
                    elif i < len(line) - 1 and line[i:i+2] == '""':
                        i += 2
                    else:
                        current += line[i]
                        i += 1
                
                if current:
                    parts.append(current)
                
                parts = [p for p in parts if p and not p.startswith(';;;;')]
                
                if parts and len(parts) > 2:
                    rows.append(parts)
        
        if len(rows) < 2:
            raise ValueError(f"Only {len(rows)} rows read")
        
        headers = rows[0]
        data_rows = rows[1:]
        
        max_cols = len(headers)
        for row in data_rows:
            while len(row) < max_cols:
                row.append('')
            if len(row) > max_cols:
                row[:] = row[:max_cols]
        
        df = pd.DataFrame(data_rows, columns=headers)
        
        cols = df.columns.tolist()
        df = df.rename(columns={cols[0]: 'Country', cols[1]: 'ISOcode'})
        
        year_cols = [col for col in df.columns if col.isdigit() and len(col) == 4]
        
        if not year_cols:
            raise ValueError("No year columns found")
        
        df = df[['Country', 'ISOcode'] + year_cols]
        
        df_melted = df.melt(
            id_vars=['Country', 'ISOcode'],
            var_name='Year',
            value_name='Life_Expectancy'
        )
        
        df_melted['Year'] = pd.to_numeric(df_melted['Year'], errors='coerce')
        df_melted['Life_Expectancy'] = pd.to_numeric(df_melted['Life_Expectancy'], errors='coerce')
        df_melted['ISOcode'] = df_melted['ISOcode'].str.strip()
        
        df_melted = df_melted.dropna(subset=['Year', 'Life_Expectancy'])
        
        df_melted["ISOcode"] = df_melted["ISOcode"].replace(ISO_CODE_MERGE_MAP)
        
        df_melted = df_melted.groupby(["ISOcode", "Year"], as_index=False)["Life_Expectancy"].mean()
        
        country_map_life = dict(zip(df['ISOcode'].str.strip(), df['Country'].str.strip('"')))
        df_melted["Country"] = df_melted["ISOcode"].map(country_map_life)
        
        df_melted = df_melted[~df_melted["ISOcode"].isin(EXCLUDED_SMALL_COUNTRY_ISOS)]
        
        return df_melted
        
    except Exception as e:
        print(f"Error loading life expectancy data: {e}")
        return pd.DataFrame(columns=['Country', 'ISOcode', 'Year', 'Life_Expectancy'])

df_life_expectancy = _apply_country_names(load_life_expectancy())


def clean_isocode(df):
    """Clean ISOcode column by removing quotes and spaces"""
    df['ISOcode'] = df['ISOcode'].astype(str).str.strip().str.replace('"', '')
    return df

def aggregate_by_year(df, year, value_col, strip_iso=False):
    """Filter by year and aggregate by ISOcode"""
    d = df[df["Year"] == year].copy()
    d["ISOcode"] = d["ISOcode"].astype(str).str.strip() if strip_iso else d["ISOcode"].astype(str)
    
    if value_col == "Life_Expectancy":
        return d.groupby("ISOcode")[value_col].mean()
    else:
        return d.groupby("ISOcode")[value_col].sum()

def map_countries_regions(df_delta, source_df):
    """Map country names and regions onto the delta dataframe"""
    iso_map = source_df.groupby("ISOcode")["Country"].first().to_dict()
    df_delta["Country"] = df_delta.index.map(lambda x: iso_map.get(x, x))
    df_delta["Region"] = df_delta.index.map(ISO_TO_REGION).fillna("Other")
    return df_delta

CONTINENT_MAP = {
    'ESP': 'Europe', 'FRA': 'Europe', 'DEU': 'Europe', 'ITA': 'Europe', 'GBR': 'Europe',
    'AND': 'Europe', 'AUT': 'Europe', 'BEL': 'Europe', 'BGR': 'Europe', 'HRV': 'Europe',
    'CYP': 'Europe', 'CZE': 'Europe', 'DNK': 'Europe', 'EST': 'Europe', 'FIN': 'Europe',
    'GRC': 'Europe', 'HUN': 'Europe', 'IRL': 'Europe', 'LVA': 'Europe', 'LTU': 'Europe',
    'LUX': 'Europe', 'MLT': 'Europe', 'NLD': 'Europe', 'POL': 'Europe', 'PRT': 'Europe',
    'ROU': 'Europe', 'SVK': 'Europe', 'SVN': 'Europe', 'SWE': 'Europe', 'CHE': 'Europe',
    'NOR': 'Europe', 'ISL': 'Europe', 'ALB': 'Europe', 'BIH': 'Europe', 'MKD': 'Europe',
    'MNE': 'Europe', 'SRB': 'Europe', 'UKR': 'Europe', 'BLR': 'Europe', 'MDA': 'Europe',
    'RUS': 'Europe', 'MCO': 'Europe', 'LIE': 'Europe', 'SMR': 'Europe', 'VAT': 'Europe',
    'GIB': 'Europe', 'FRO': 'Europe', 'GGY': 'Europe', 'JEY': 'Europe', 'IMN': 'Europe',
    'XKX': 'Europe', 'GEO': 'Europe', 'ARM': 'Europe', 'AZE': 'Europe',
    
    'CHN': 'Asia', 'IND': 'Asia', 'JPN': 'Asia', 'KOR': 'Asia', 'IDN': 'Asia',
    'THA': 'Asia', 'VNM': 'Asia', 'PAK': 'Asia', 'BGD': 'Asia', 'PHL': 'Asia',
    'MYS': 'Asia', 'SGP': 'Asia', 'IRN': 'Asia', 'IRQ': 'Asia', 'SAU': 'Asia',
    'ARE': 'Asia', 'KWT': 'Asia', 'QAT': 'Asia', 'OMN': 'Asia', 'BHR': 'Asia',
    'ISR': 'Asia', 'JOR': 'Asia', 'LBN': 'Asia', 'SYR': 'Asia', 'TUR': 'Asia',
    'YEM': 'Asia', 'AFG': 'Asia', 'KAZ': 'Asia', 'UZB': 'Asia', 'TKM': 'Asia',
    'KGZ': 'Asia', 'TJK': 'Asia', 'NPL': 'Asia', 'BTN': 'Asia', 'LKA': 'Asia',
    'MDV': 'Asia', 'MMR': 'Asia', 'LAO': 'Asia', 'KHM': 'Asia', 'BRN': 'Asia',
    'MNG': 'Asia', 'PRK': 'Asia', 'TWN': 'Asia', 'HKG': 'Asia', 'MAC': 'Asia',
    'PSE': 'Asia', 'TLS': 'Asia',
    
    'USA': 'America', 'CAN': 'America', 'MEX': 'America', 'GRL': 'America',
    
    'GTM': 'America', 'BLZ': 'America', 'SLV': 'America', 'HND': 'America', 'NIC': 'America',
    'CRI': 'America', 'PAN': 'America', 'CUB': 'America', 'HTI': 'America', 'DOM': 'America',
    'JAM': 'America', 'TTO': 'America', 'BHS': 'America', 'BRB': 'America', 'GRD': 'America',
    'LCA': 'America', 'VCT': 'America', 'ATG': 'America', 'DMA': 'America', 'KNA': 'America',
    
    'BRA': 'America', 'ARG': 'America', 'CHL': 'America', 'COL': 'America', 'PER': 'America',
    'VEN': 'America', 'ECU': 'America', 'BOL': 'America', 'PRY': 'America', 'URY': 'America',
    'GUY': 'America', 'SUR': 'America', 'GUF': 'America',
    
    'ZAF': 'Africa', 'EGY': 'Africa', 'NGA': 'Africa', 'KEN': 'Africa', 'ETH': 'Africa',
    'GHA': 'Africa', 'TZA': 'Africa', 'UGA': 'Africa', 'DZA': 'Africa', 'MAR': 'Africa',
    'AGO': 'Africa', 'SEN': 'Africa', 'CMR': 'Africa', 'CIV': 'Africa', 'TUN': 'Africa',
    'LBY': 'Africa', 'SDN': 'Africa', 'SSD': 'Africa', 'SOM': 'Africa', 'ERI': 'Africa',
    'DJI': 'Africa', 'RWA': 'Africa', 'BDI': 'Africa', 'MOZ': 'Africa', 'ZWE': 'Africa',
    'BWA': 'Africa', 'NAM': 'Africa', 'LSO': 'Africa', 'SWZ': 'Africa', 'MWI': 'Africa',
    'ZMB': 'Africa', 'MDG': 'Africa', 'MUS': 'Africa', 'SYC': 'Africa', 'COM': 'Africa',
    'COD': 'Africa', 'COG': 'Africa', 'GAB': 'Africa', 'GNQ': 'Africa', 'CAF': 'Africa',
    'TCD': 'Africa', 'MLI': 'Africa', 'NER': 'Africa', 'BFA': 'Africa', 'BEN': 'Africa',
    'TGO': 'Africa', 'GIN': 'Africa', 'GNB': 'Africa', 'SLE': 'Africa', 'LBR': 'Africa',
    'MRT': 'Africa', 'GMB': 'Africa', 'CPV': 'Africa', 'STP': 'Africa',
    
    'AUS': 'Oceania', 'NZL': 'Oceania', 'FJI': 'Oceania', 'PNG': 'Oceania',
    'NCL': 'Oceania', 'PYF': 'Oceania', 'GUM': 'Oceania', 'VUT': 'Oceania',
    'SLB': 'Oceania', 'WSM': 'Oceania', 'KIR': 'Oceania', 'TON': 'Oceania',
    'FSM': 'Oceania', 'PLW': 'Oceania', 'MHL': 'Oceania', 'NRU': 'Oceania',
    'TUV': 'Oceania', 'ASM': 'Oceania', 'MNP': 'Oceania'
}   