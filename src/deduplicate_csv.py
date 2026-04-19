#!/usr/bin/env python3
"""
Script to deduplicate the combined CSV file by grouping on all columns except 'Extraction Date',
and adding two new columns: 'First Extraction Date' and 'Last Extraction Date'.
Also cleans numeric fields and dates, and merges specified column pairs (keeping the second).
Handles city and Municipio: merge Municipio into city, keeping city in dictionary format.
Sets neighborhood to empty if it is "NA".
Merges Barrio into commonNeighborhood, keeping commonNeighborhood.
Merges code into propertyId, keeping propertyId.
Transforms builtTime into two columns: builtTime_min_year and builtTime_max_year based on the last extraction date.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

def clean_price(val):
    """Remove $ and commas, convert to float. If empty or invalid, return empty string."""
    if not val:
        return ''
    # If already a number, return as float
    if isinstance(val, (int, float)):
        return float(val)
    # Remove $ and commas
    cleaned = str(val).replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return val  # return original if conversion fails

def clean_area(val):
    """Extract numeric part, remove any non-digit, non-decimal point, and commas, convert to float."""
    if not val:
        return ''
    # If already a number, return as float
    if isinstance(val, (int, float)):
        return float(val)
    # Remove commas first
    cleaned = str(val).replace(',', '')
    # Extract the first number (integer or float) from the string
    # This will handle cases like "55m", "57.5m", etc.
    match = re.search(r'[\d]+(?:\.[\d]+)?', cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return val
    return val

def clean_int(val):
    """Remove commas and convert to int. If empty or invalid, return empty string."""
    if not val:
        return ''
    # If already an int, return as int
    if isinstance(val, int):
        return val
    # If it's a float that is an integer, convert to int
    if isinstance(val, float) and val.is_integer():
        return int(val)
    cleaned = str(val).replace(',', '')
    try:
        return int(cleaned)
    except ValueError:
        return val

def clean_date(val):
    """Ensure date is in YYYY-MM-DD format. If empty, return empty string."""
    if not val:
        return ''
    # Basic validation: check if it matches YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', str(val)):
        return str(val)
    # If not, try to extract? For simplicity, return original.
    return val

def clean_city_municipio(row):
    """Handle city and Municipio: merge Municipio into city, keeping city in dictionary format."""
    # Make a copy to avoid modifying original during iteration
    cleaned = row.copy()
    city_val = cleaned.get('city', '')
    municipio_val = cleaned.get('Municipio', '')
    
    # Helper to check if a string looks like a dictionary
    def is_dict_string(s):
        return isinstance(s, str) and s.startswith('{') and s.endswith('}') and "'id'" in s and "'nombre'" in s
    
    # If city is already a dictionary string, keep it
    if city_val and is_dict_string(city_val):
        cleaned['city'] = city_val
    else:
        # If city is empty or not a dict, try to use Municipio
        if municipio_val:
            # Convert Municipio to dictionary format: {'id': '', 'nombre': '<value>'}
            # Escape any single quotes inside the value? For simplicity, we assume no quotes.
            cleaned['city'] = f"{{'id': '', 'nombre': '{municipio_val}'}}"
        else:
            # If both empty, set city to empty string
            cleaned['city'] = ''
    
    # Remove Municipio column
    if 'Municipio' in cleaned:
        del cleaned['Municipio']
    return cleaned

def clean_neighborhood(val):
    """If neighborhood is 'NA', set to empty string."""
    if not val:
        return val
    if str(val).strip() == 'NA':
        return ''
    return val

def clean_barrio_commonneighborhood(row):
    """Merge Barrio into commonNeighborhood, keeping commonNeighborhood."""
    cleaned = row.copy()
    barrio_val = cleaned.get('Barrio', '')
    common_neighborhood_val = cleaned.get('commonNeighborhood', '')
    # Choose commonNeighborhood if not empty, else Barrio
    if common_neighborhood_val != '':
        cleaned['commonNeighborhood'] = common_neighborhood_val
    else:
        cleaned['commonNeighborhood'] = barrio_val
    # Remove Barrio column
    if 'Barrio' in cleaned:
        del cleaned['Barrio']
    return cleaned

def clean_code_propertyid(row):
    """Merge code into propertyId, keeping propertyId."""
    cleaned = row.copy()
    code_val = cleaned.get('code', '')
    property_id_val = cleaned.get('propertyId', '')
    # Choose propertyId if not empty, else code
    if property_id_val != '':
        cleaned['propertyId'] = property_id_val
    else:
        cleaned['propertyId'] = code_val
    # Remove code column
    if 'code' in cleaned:
        del cleaned['code']
    return cleaned

def parse_builtTime(builtTime_str):
    """Parse builtTime string and return (min_years, max_years) as integers.
       If the string is empty or not recognized, return (None, None).
    """
    if not builtTime_str or not isinstance(builtTime_str, str):
        return (None, None)
    s = builtTime_str.strip()
    # Handle Remodelado as Entre 0 y 5 años
    if s == 'Remodelado':
        s = 'Entre 0 y 5 años'
    # Handle Más de 20 años as Entre 20 y 40 años
    if s == 'Más de 20 años':
        s = 'Entre 20 y 40 años'
    # Extract numbers from strings like "Entre X y Y años"
    match = re.search(r'Entre\s+(\d+)\s+y\s+(\d+)\s+años', s, re.IGNORECASE)
    if match:
        try:
            low = int(match.group(1))
            high = int(match.group(2))
            return (low, high)
        except ValueError:
            return (None, None)
    return (None, None)

def clean_numeric_fields(row):
    """Clean specific numeric fields in the row, and merge specified column pairs (keeping the second)."""
    # Make a copy to avoid modifying original during iteration
    cleaned = row.copy()
    # First handle city and Municipio
    cleaned = clean_city_municipio(cleaned)
    # Then handle Barrio and commonNeighborhood
    cleaned = clean_barrio_commonneighborhood(cleaned)
    # Then handle code and propertyId
    cleaned = clean_code_propertyid(cleaned)
    # Price fields
    if 'Precio' in cleaned:
        cleaned['Precio'] = clean_price(cleaned['Precio'])
    if 'salePrice' in cleaned:
        cleaned['salePrice'] = clean_price(cleaned['salePrice'])
    # Area fields
    if 'area' in cleaned:
        cleaned['area'] = clean_area(cleaned['area'])
    if 'areac' in cleaned:
        cleaned['areac'] = clean_area(cleaned['areac'])
    if 'Área' in cleaned:  # note: special character
        cleaned['Área'] = clean_area(cleaned['Área'])
    # Bathrooms: merge Baños and bathrooms into bathrooms
    banos_val = ''
    if 'Baños' in cleaned:
        banos_val = clean_int(cleaned['Baños'])
    bathrooms_val = ''
    if 'bathrooms' in cleaned:
        bathrooms_val = clean_int(cleaned['bathrooms'])
    # Choose bathrooms if not empty, else Baños
    if bathrooms_val != '':
        cleaned['bathrooms'] = bathrooms_val
    else:
        cleaned['bathrooms'] = banos_val
    # Remove the Baños column
    if 'Baños' in cleaned:
        del cleaned['Baños']
    # Garages: merge Garajes and garages into garages
    garajes_val = ''
    if 'Garajes' in cleaned:
        garajes_val = clean_int(cleaned['Garajes'])
    garages_val = ''
    if 'garages' in cleaned:
        garages_val = clean_int(cleaned['garages'])
    # Choose garages if not empty, else Garajes
    if garages_val != '':
        cleaned['garages'] = garajes_val
    else:
        cleaned['garages'] = garajes_val
    # Remove the Garajes column
    if 'Garajes' in cleaned:
        del cleaned['Garajes']
    # Habitaciones: merge Habitaciones and rooms into rooms
    habitaciones_val = ''
    if 'Habitaciones' in cleaned:
        habitaciones_val = clean_int(cleaned['Habitaciones'])
    rooms_val = ''
    if 'rooms' in cleaned:
        rooms_val = clean_int(cleaned['rooms'])
    # Choose rooms if not empty, else Habitaciones
    if rooms_val != '':
        cleaned['rooms'] = rooms_val
    else:
        cleaned['rooms'] = habitaciones_val
    # Remove the Habitaciones column
    if 'Habitaciones' in cleaned:
        del cleaned['Habitaciones']
    # Área: merge Área and area into area
    area_val = ''
    if 'Área' in cleaned:
        area_val = clean_area(cleaned['Área'])
    area_val2 = ''
    if 'area' in cleaned:
        area_val2 = clean_area(cleaned['area'])
    # Choose area if not empty, else Área
    if area_val2 != '':
        cleaned['area'] = area_val2
    else:
        cleaned['area'] = area_val
    # Remove the Área column
    if 'Área' in cleaned:
        del cleaned['Área']
    # Closets
    if 'Closets' in cleaned:
        cleaned['Closets'] = clean_int(cleaned['Closets'])
    # builtTime: we keep as string for now, will be transformed later
    # stratum
    if 'stratum' in cleaned:
        cleaned['stratum'] = clean_int(cleaned['stratum'])
    # adminPrice: clean as price, then if 0 set to empty string
    if 'adminPrice' in cleaned:
        admin_price = clean_price(cleaned['adminPrice'])
        # If the cleaned admin price is 0 (or 0.0), set to empty string
        if isinstance(admin_price, (int, float)) and admin_price == 0:
            cleaned['adminPrice'] = ''
        else:
            cleaned['adminPrice'] = admin_price
    # Extraction Date
    if 'Extraction Date' in cleaned:
        cleaned['Extraction Date'] = clean_date(cleaned['Extraction Date'])
    # Neighborhood: set to empty if "NA"
    if 'neighborhood' in cleaned:
        cleaned['neighborhood'] = clean_neighborhood(cleaned['neighborhood'])
    return cleaned

def deduplicate_csv():
    input_file = Path('data/combined_listings.csv')
    output_file = Path('data/combined_listings_deduplicated.csv')
    
    # Read the input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            print("Error: No headers found in the input CSV.")
            return
        
        # Check if 'Extraction Date' column exists
        if 'Extraction Date' not in fieldnames:
            print("Error: 'Extraction Date' column not found in the input CSV.")
            return
        
        # Prepare grouping: key is tuple of values for all columns except 'Extraction Date' (after cleaning)
        # We will exclude the columns that we plan to remove (the first of each pair) from the key.
        # Columns to remove: Baños, Garajes, Habitaciones, Precio, Área, Municipio, Barrio, code
        columns_to_remove = {'Baños', 'Garajes', 'Habitaciones', 'Precio', 'Área', 'Municipio', 'Barrio', 'code'}
        groups = defaultdict(list)  # key -> list of (original row, cleaned Extraction Date)
        
        for row in reader:
            cleaned_row = clean_numeric_fields(row)
            # Create a key from all columns except 'Extraction Date' and the columns we remove (using cleaned values)
            key_cols = [col for col in fieldnames if col != 'Extraction Date' and col not in columns_to_remove]
            key = tuple(cleaned_row[col] for col in key_cols)
            extraction_date = cleaned_row['Extraction Date']
            groups[key].append((row, extraction_date))  # store original row for reference? We'll use cleaned values for output.
    
    # Prepare output fieldnames: original columns except 'Extraction Date' and the columns we remove, plus the two new date columns
    # We also remove builtTime and add two new columns: builtTime_min_year and builtTime_max_year
    output_fieldnames = [col for col in fieldnames if col != 'Extraction Date' and col not in columns_to_remove and col != 'builtTime'] + ['First Extraction Date', 'Last Extraction Date', 'builtTime_min_year', 'builtTime_max_year']
    
    # Write the output CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        
        for key, items in groups.items():
            # items is list of (original row, extraction_date)
            # We'll use the cleaned values from the first item for the key columns (they should be same after cleaning)
            first_original, first_date = items[0]
            cleaned_first = clean_numeric_fields(first_original)
            # Build the row for the key columns (excluding Extraction Date, the columns we remove, and builtTime)
            row = {col: cleaned_first[col] for col in [col for col in fieldnames if col != 'Extraction Date' and col not in columns_to_remove and col != 'builtTime']}
            # Extract all dates for this group
            dates = [item[1] for item in items]  # cleaned extraction dates
            # Filter out empty dates
            non_empty_dates = [d for d in dates if d]
            if non_empty_dates:
                first_date = min(non_empty_dates)
                last_date = max(non_empty_dates)
            else:
                first_date = ''
                last_date = ''
            row['First Extraction Date'] = first_date
            row['Last Extraction Date'] = last_date
            
            # Now compute the two builtTime columns for each item in the group and take the min and max? 
            # Actually, the user wants to transform the builtTime column for each row.
            # But we have deduplicated: each group represents a set of rows that are identical in all columns except Extraction Date.
            # However, the builtTime column is part of the key (we did not remove it from the key) so all items in the group have the same builtTime string.
            # Therefore, we can compute the two new columns from the builtTime string of the first item and the group's last_date.
            builtTime_str = first_original.get('builtTime', '')
            low, high = parse_builtTime(builtTime_str)
            # Extract year from last_date (format YYYY-MM-DD)
            year = None
            if last_date and re.match(r'^\d{4}-\d{2}-\d{2}$', last_date):
                try:
                    year = int(last_date.split('-')[0])
                except ValueError:
                    year = None
            if year is not None and low is not None and high is not None:
                builtTime_min_year = year - low
                builtTime_max_year = year - high
                # Note: the user said first column is latest extraction date minus the first number, second column minus the second number.
                # So we have:
                #   builtTime_min_year = year - low   (which is the larger year? because low is the smaller number)
                #   builtTime_max_year = year - high  (which is the smaller year)
                # But the user didn't specify which is min or max. We'll keep as computed.
            else:
                builtTime_min_year = ''
                builtTime_max_year = ''
            row['builtTime_min_year'] = builtTime_min_year
            row['builtTime_max_year'] = builtTime_max_year
            writer.writerow(row)
    
    print(f"Successfully deduplicated {len(groups)} unique rows from {input_file} to {output_file}")

if __name__ == '__main__':
    deduplicate_csv()