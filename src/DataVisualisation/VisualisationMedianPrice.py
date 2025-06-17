# %%
# Import required libraries for data manipulation, geospatial analysis, and visualization
import pandas as pd
import geopandas as gpd
import ast
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
import glob
import numpy as np
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from adjustText import adjust_text
import matplotlib.image as mpimg



# %%
# Set the property type and time period for analysis
property_type = 'Apartments' # Options: 'Houses', 'Apartments', 'Offices'
# Note: Some house data may have incorrect coordinates, especially for certain neighborhoods
year = 2025
quarter = 1  # Desired quarter for analysis (1, 2, 3, or 4)


# %%
# Find all CSV files for the selected property type and city
csv_files = glob.glob(f'../../data/{property_type}/listings_data_m2_medellin*.csv')

# Read and concatenate all CSV files into a single DataFrame for analysis
df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

# %%
# Convert 'Extraction Date' column to datetime format if not already
df['Extraction Date'] = pd.to_datetime(df['Extraction Date'])

# Filter data for the selected quarter and year
start_month = 3 * (quarter - 1) + 1
end_month = start_month + 2
mask = (
    (df['Extraction Date'].dt.year == year) &
    (df['Extraction Date'].dt.month >= start_month) &
    (df['Extraction Date'].dt.month <= end_month)
)
df =  df[mask]


# %%
# Sort the DataFrame by extraction date (most recent first)
df.sort_values('Extraction Date', ascending=False, inplace=True)

# Remove duplicate property listings, keeping only the most recent entry for each propertyId
df.drop_duplicates(subset='propertyId', inplace=True, keep='first')

# %%
# Calculate price per square meter for each property
df['price_per_m2'] = df['salePrice'] / df['area']

# Extract longitude and latitude from the 'coordinates' column
df['coordinates'] = df['coordinates'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
df['lon'] = df['coordinates'].apply(lambda x: x.get('lon') if isinstance(x, dict) else None)
df['lat'] = df['coordinates'].apply(lambda x: x.get('lat') if isinstance(x, dict) else None)

# Remove rows with missing or zero coordinates
df = df[(df['lon'] != 0.0) & (df['lat'] != 0.0)]
df_map = df.dropna(subset=['lon', 'lat'])



# %%
# Load the shapefile for neighborhoods (barrios) and corregimientos
# These files contain the geographic boundaries for spatial analysis
gdf = gpd.read_file('Inputs/shp_barrios_y_veredas/barrios_y_veredas.shp')
gdf_corregimientos = gpd.read_file('Inputs/shp_comunas_y_corregimientos_/comunas_y_corregimientos_.shp')

# Filter out rows with missing neighborhood names
gdf = gdf[gdf['nombre'].notna()]



# %%
# Get the geometry for 'El Poblado' from the corregimientos shapefile
el_poblado_geom = gdf_corregimientos[gdf_corregimientos['nombre'] == 'El Poblado']['geometry'].iloc[0]

# Filter neighborhoods (barrios) that are within 'El Poblado' or are specific named areas
# This creates a GeoDataFrame for the sub-neighborhoods of El Poblado
gdf_el_poblado = gdf[gdf.within(el_poblado_geom) | 
                    (gdf['nombre'] == 'La Aguacatala') |
                    (gdf['nombre'] == 'Santa María de Los Ángeles') |
                    (gdf['nombre'] == 'El Tesoro') ].copy()


# %%
# Ensure the GeoDataFrame is in the same CRS as the coordinates (EPSG:4326)
gdf_4326 = gdf_el_poblado.to_crs(epsg=4326)

# Create a geometry column in df_map for spatial operations
df_map['geometry'] = df_map.apply(lambda row: Point(row['lon'], row['lat']), axis=1)

# Convert df_map to a GeoDataFrame for spatial join
gdf_points = gpd.GeoDataFrame(df_map, geometry='geometry', crs='EPSG:4326')

# Perform a spatial join to assign each property to a neighborhood
gdf_points = gpd.sjoin(gdf_points, gdf_4326[['nombre', 'geometry']], how='left', predicate='within')

# Add the neighborhood name from the shapefile as a new column in df_map
df_map['neighbourhood_from_shape'] = gdf_points['nombre']


# %%
# Calculate average and median sale price for each neighborhood in df_map
avg_price_by_neigh = df_map.groupby('neighbourhood_from_shape')['salePrice'].mean()
median_price_by_neigh = df_map.groupby('neighbourhood_from_shape')['salePrice'].median()

# Calculate the Semi-Interquartile Range (SIQR) for each neighbourhood
q1 = df_map.groupby('neighbourhood_from_shape')['salePrice'].quantile(0.25)
q3 = df_map.groupby('neighbourhood_from_shape')['salePrice'].quantile(0.75)
siqr_by_neigh = (q3 - q1) / 2

# Map SIQR to the gdf_4326 GeoDataFrame
gdf_4326['siqr'] = gdf_4326['nombre'].map(siqr_by_neigh)


# Calculate the number of properties per neighbourhood
count_by_neigh = df_map.groupby('neighbourhood_from_shape')['salePrice'].count()
gdf_4326['num_properties'] = gdf_4326['nombre'].map(count_by_neigh).fillna(0).astype(int)

# Map the average price to the gdf_4326 GeoDataFrame based on 'nombre'
gdf_4326['avg_price'] = gdf_4326['nombre'].map(avg_price_by_neigh)
gdf_4326['median_price'] = gdf_4326['nombre'].map(median_price_by_neigh)


# If the number of properties is less than 5, make the avg_price equal to nan
min_properties = 5
gdf_4326.loc[gdf_4326['num_properties'] < min_properties, 'avg_price'] = np.nan
gdf_4326.loc[gdf_4326['num_properties'] < min_properties, 'median_price'] = np.nan




# %%
# Set the map provider for the basemap
map_provider = 'OPNVKarte'

# Set the font to Roboto for the entire figure
plt.rcParams['font.family'] = 'Roboto'

# Create the figure and axis for plotting
fig, ax = plt.subplots(figsize=(12, 12))

# Filter neighborhoods with valid (non-NaN, non-zero) median prices
gdf_4326_valid = gdf_4326[gdf_4326['median_price'].notna() & (gdf_4326['median_price'] != 0)]

# Define a custom color palette for the map
colors = [
    (102/255, 99/255, 91/255),    # GrayDark
    (179/255, 179/255, 179/255), # GrayLight
    (0/255, 195/255, 255/255),   # BlueLight
    (5/255, 71/255, 127/255),    # BlueDarkDark
    (12/255, 58/255, 229/255),    # BlueDark
]

# Create the colormap from the custom color list
my_cmap = LinearSegmentedColormap.from_list("my_custom_colormap", colors)

# Set the transparency
alpha_value = 0.8


# Plot the valid neighborhoods colored by median price
plot = gdf_4326_valid.plot(
    column='median_price', ax=ax, legend=True, cmap=my_cmap, edgecolor='k', alpha=alpha_value
)

# Draw the edges of all neighborhoods (including those without data)
gdf_4326.plot(facecolor='none', ax=ax, edgecolor='k', linewidth=3)

#making the map square, for instagram
xlim = ax.get_xlim()
ylim = ax.get_ylim()
x_mid = (xlim[1] + xlim[0])/2
y_range = ylim[1] - ylim[0]
ax.set_xlim(x_mid-0.5*y_range, x_mid+0.5*y_range)


# Add the basemap tiles to the plot
source = ctx.providers[map_provider]
ctx.add_basemap(ax, crs=gdf_4326.crs.to_string(), source=source)

# Set the plot title and remove axis
if property_type == 'Apartments':
    property_type_label = 'Apartamentos Usados'
elif property_type == 'Houses':
    property_type_label = 'Casas Usadas'
elif property_type == 'Offices':
    property_type_label = 'Oficinas Usadas'

plt.rcParams.update({'axes.titlesize': 18})
# plt.title(f'El Poblado - Medellín\nPrecio de Venta {property_type_label}\nQ{quarter} - {year}')
title_string = (
    r'$\bf{' f'El\ Poblado - Medellín' r'}$' + 
    '\n' +
    r'Precio de Venta ' f'{property_type_label}' + 
    '\n' +
    r'Q' f'{quarter}' r' - ' f'{year}'
)


plt.title(title_string)
plt.axis('off')

# Format the colorbar to show values in millions of COP
cbar = plot.get_figure().axes[-1]
cbar.set_ylabel('MCOP')
cbar.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1e6:.0f}'))
for c in cbar.collections:
    c.set_alpha(alpha_value)

# Set the size of the numbers in the colorbar
cbar.tick_params(labelsize=11)

# Adjust colorbar height to match the y-axis range
cbar = plot.get_figure().axes[-1]
fig = plot.get_figure()
# Get position of the main axis and colorbar axis
ax_pos = ax.get_position()
cbar_pos = cbar.get_position()
# Set colorbar height to match the main axis height (ylim)
cbar.set_position([
    cbar_pos.x0,
    ax_pos.y0,
    cbar_pos.width,
    ax_pos.height
])

# Import adjust_text for text overlap prevention

# Create list to store text annotations
texts = []

# Create annotations for each neighborhood
for idx, row in gdf_4326.iterrows():
    centroid = row['geometry'].centroid
    neighbourhood_name = row['nombre']
    median_price = row['median_price']
    if not np.isnan(median_price) and median_price != 0:
        value = median_price / 1e6
        label = f'{neighbourhood_name}\n{value:,.0f} MCOP'
    else:
        label = f'{neighbourhood_name}'
    
    text = ax.text(
        centroid.x, centroid.y,
        label,
        color='black',
        fontsize=10,
        ha='center',
        va='center',
        fontweight='bold',
        bbox=dict(facecolor='white', alpha=alpha_value, edgecolor='none', boxstyle='round,pad=0.2')
    )
    texts.append(text)

# Adjust text positions to prevent overlap
adjust_text(
    texts,
    force_points=0.2,
    force_text=0.5,
    expand_points=(1.2, 1.2),
    expand_text=(1.2, 1.2),
    # arrowprops=dict(arrowstyle="-", color='gray', lw=0.5)
)

# Add a logo to the bottom left of the plot
logo_path = 'Inputs/LogoOriginal.png'
logo_img = mpimg.imread(logo_path)
imagebox = OffsetImage(logo_img, zoom=0.3)  # Adjust zoom as needed

# Position: (x0, y0) in axes fraction coordinates (0,0 is bottom left)
ab = AnnotationBbox(
    imagebox,
    (0.845, 0.01),  # Adjust as needed for position
    xycoords='axes fraction',
    frameon=False,
    box_alignment=(0, 0)
)
ax.add_artist(ab)

# Add "@AldeaAI" text to top right corner
# Add Instagram logo (using unicode character) and @AldeaAI text
ax.text(
    0.99, 0.99,
    '\u2002\uf16d  @AldeaAI',  # Unicode for Instagram logo + text
    transform=ax.transAxes,
    fontsize=14,
    fontweight='bold',
    color='black',
    ha='right',
    va='top',
    bbox=dict(facecolor='white', alpha=alpha_value, edgecolor='none', boxstyle='round,pad=0.2'),
    fontname='FontAwesome'  # Requires FontAwesome font to be installed
)

# Display the plot
# plt.show()


# Save the plot to a file
filename = f'{year}_Q{quarter}_median_price_{property_type}_ElPoblado_map.png'
fig.savefig(f'../../DataVisualisation/{filename}', dpi=80, bbox_inches='tight')
# fig.savefig(f'../../DataVisualisation/{filename}', dpi=80)



# %%
# Descubre cómo varían los precios medianos de venta de apartamentos en los barrios de El Poblado, Medellín 🏙️📊. Este mapa muestra las diferencias entre sectores durante el primer trimestre de 2025. ¿En qué barrio te gustaría vivir? #Medellín #ElPoblado #Inmobiliaria #Datos #Vivienda #RealEstate #DataViz




