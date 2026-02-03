import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table

# data
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

df_totals = safe_load_and_melt('totals', ['Country', 'ISOcode'])
df_capita = safe_load_and_melt('capita', ['Country', 'ISOcode'])
df_sectors = safe_load_and_melt('sector', ['Country', 'ISOcode', 'Sector'])
df_correlation = get_correlation_data()  # Assuming this function is defined elsewhere
df_cumulative = get_cumulative_data()  # Assuming this function is defined elsewhere

# Variables de control para el slider de la App
min_year = int(df_totals['Year'].min())
max_year = int(df_totals['Year'].max())

continent_map = {
    # África
    'Algeria': 'África', 'Angola': 'África', 'Benin': 'África', 'Botswana': 'África', 'Burkina Faso': 'África', 'Burundi': 'África', 'Cameroon': 'África', 'Cape Verde': 'África', 'Central African Republic': 'África', 'Chad': 'África', 'Comoros': 'África', 'Congo': 'África', 'Democratic Republic of Congo': 'África', 'Djibouti': 'África', 'Egypt': 'África', 'Equatorial Guinea': 'África', 'Eritrea': 'África', 'Ethiopia': 'África', 'Gabon': 'África', 'Gambia': 'África', 'Ghana': 'África', 'Guinea': 'África', 'Guinea-Bissau': 'África', 'Ivory Coast': 'África', 'Kenya': 'África', 'Lesotho': 'África', 'Liberia': 'África', 'Libya': 'África', 'Madagascar': 'África', 'Malawi': 'África', 'Mali': 'África', 'Mauritania': 'África', 'Mauritius': 'África', 'Morocco': 'África', 'Mozambique': 'África', 'Namibia': 'África', 'Niger': 'África', 'Nigeria': 'África', 'Rwanda': 'África', 'Sao Tome and Principe': 'África', 'Senegal': 'África', 'Seychelles': 'África', 'Sierra Leone': 'África', 'Somalia': 'África', 'South Africa': 'África', 'South Sudan': 'África', 'Sudan': 'África', 'Swaziland': 'África', 'Tanzania': 'África', 'Togo': 'África', 'Tunisia': 'África', 'Uganda': 'África', 'Zambia': 'África', 'Zimbabwe': 'África',
    
    # Asia
    'Afghanistan': 'Asia', 'Armenia': 'Asia', 'Azerbaijan': 'Asia', 'Bahrain': 'Asia', 'Bangladesh': 'Asia', 'Bhutan': 'Asia', 'Brunei': 'Asia', 'Cambodia': 'Asia', 'China': 'Asia', 'Cyprus': 'Asia', 'Georgia': 'Asia', 'India': 'Asia', 'Indonesia': 'Asia', 'Iran': 'Asia', 'Iraq': 'Asia', 'Israel': 'Asia', 'Japan': 'Asia', 'Jordan': 'Asia', 'Kazakhstan': 'Asia', 'Kuwait': 'Asia', 'Kyrgyzstan': 'Asia', 'Laos': 'Asia', 'Lebanon': 'Asia', 'Malaysia': 'Asia', 'Maldives': 'Asia', 'Mongolia': 'Asia', 'Myanmar': 'Asia', 'Nepal': 'Asia', 'North Korea': 'Asia', 'Oman': 'Asia', 'Pakistan': 'Asia', 'Palestine': 'Asia', 'Philippines': 'Asia', 'Qatar': 'Asia', 'Saudi Arabia': 'Asia', 'Singapore': 'Asia', 'South Korea': 'Asia', 'Sri Lanka': 'Asia', 'Syria': 'Asia', 'Taiwan': 'Asia', 'Tajikistan': 'Asia', 'Thailand': 'Asia', 'Timor': 'Asia', 'Turkey': 'Asia', 'Turkmenistan': 'Asia', 'United Arab Emirates': 'Asia', 'Uzbekistan': 'Asia', 'Vietnam': 'Asia', 'Yemen': 'Asia',
    
    # Europa
    'Albania': 'Europa', 'Andorra': 'Europa', 'Austria': 'Europa', 'Belarus': 'Europa', 'Belgium': 'Europa', 'Bosnia and Herzegovina': 'Europa', 'Bulgaria': 'Europa', 'Croatia': 'Europa', 'Czech Republic': 'Europa', 'Denmark': 'Europa', 'Estonia': 'Europa', 'Finland': 'Europa', 'France': 'Europa', 'Germany': 'Europa', 'Greece': 'Europa', 'Hungary': 'Europa', 'Iceland': 'Europa', 'Ireland': 'Europa', 'Italy': 'Europa', 'Latvia': 'Europa', 'Liechtenstein': 'Europa', 'Lithuania': 'Europa', 'Luxembourg': 'Europa', 'Malta': 'Europa', 'Moldova': 'Europa', 'Monaco': 'Europa', 'Montenegro': 'Europa', 'Netherlands': 'Europa', 'North Macedonia': 'Europa', 'Norway': 'Europa', 'Poland': 'Europa', 'Portugal': 'Europa', 'Romania': 'Europa', 'Russia': 'Europa', 'San Marino': 'Europa', 'Serbia': 'Europa', 'Slovakia': 'Europa', 'Slovenia': 'Europa', 'Spain': 'Europa', 'Sweden': 'Europa', 'Switzerland': 'Europa', 'Ukraine': 'Europa', 'United Kingdom': 'Europa',
    
    # América (Norte y Sur)
    'Antigua and Barbuda': 'América', 'Bahamas': 'América', 'Barbados': 'América', 'Belize': 'América', 'Canada': 'América', 'Costa Rica': 'América', 'Cuba': 'América', 'Dominica': 'América', 'Dominican Republic': 'América', 'El Salvador': 'América', 'Grenada': 'América', 'Guatemala': 'América', 'Haiti': 'América', 'Honduras': 'América', 'Jamaica': 'América', 'Mexico': 'América', 'Nicaragua': 'América', 'Panama': 'América', 'Saint Kitts and Nevis': 'América', 'Saint Lucia': 'América', 'Saint Vincent and the Grenadines': 'América', 'Trinidad and Tobago': 'América', 'USA': 'América', 'United States': 'América',
    'Argentina': 'América', 'Bolivia': 'América', 'Brazil': 'América', 'Chile': 'América', 'Colombia': 'América', 'Ecuador': 'América', 'Guyana': 'América', 'Paraguay': 'América', 'Peru': 'América', 'Suriname': 'América', 'Uruguay': 'América', 'Venezuela': 'América',
    
    # Oceanía
    'Australia': 'Oceania', 'Fiji': 'Oceania', 'Kiribati': 'Oceania', 'Marshall Islands': 'Oceania', 'Micronesia': 'Oceania', 'Nauru': 'Oceania', 'New Zealand': 'Oceania', 'Palau': 'Oceania', 'Papua New Guinea': 'Oceania', 'Samoa': 'Oceania', 'Solomon Islands': 'Oceania', 'Tonga': 'Oceania', 'Tuvalu': 'Oceania', 'Vanuatu': 'Oceania'
}

# Aplicar al DataFrame en prepare_data.py
df_totals['Continent'] = df_totals['Country'].map(continent_map).fillna('Otros')