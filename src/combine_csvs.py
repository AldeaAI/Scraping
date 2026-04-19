#!/usr/bin/env python3
"""
Script to combine all CSV files from data/ subfolders into a single CSV file.
Handles different headers by taking the union of all columns and filling missing values with empty strings.
Also adds a temporary source_folder column to infer missing propertyType, then removes it.
"""

import os
import csv
from pathlib import Path

def combine_csv_files():
    data_dir = Path('data')
    output_file = Path('data/combined_listings.csv')
    
    # Find all CSV files in subdirectories
    csv_files = list(data_dir.glob('*/*.csv'))
    print(f"Found {len(csv_files)} CSV files to combine")
    
    # Collect all unique column names
    all_columns = set()
    file_data = []  # List of (filename, rows, source_folder) tuples
    
    for csv_file in csv_files:
        # Determine source folder from the parent directory name
        source_folder = csv_file.parent.name  # Apartments, Houses, or Offices
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Try to detect dialect
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                f.seek(0)
                
                reader = csv.DictReader(f, dialect=dialect)
                if reader.fieldnames:
                    all_columns.update(reader.fieldnames)
                    rows = list(reader)
                    file_data.append((csv_file.name, rows, source_folder))
                    print(f"  {csv_file.name}: {len(rows)} rows, columns: {reader.fieldnames}")
                else:
                    print(f"  {csv_file.name}: No headers found or empty file")
        except Exception as e:
            print(f"  Error reading {csv_file.name}: {e}")
    
    if not all_columns:
        print("No columns found in any CSV files")
        return
    
    # Convert to sorted list for consistent column order
    all_columns = sorted(list(all_columns))
    print(f"\nCombined columns ({len(all_columns)}): {all_columns}")
    
    # Write combined CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        
        total_rows = 0
        for filename, rows, source_folder in file_data:
            for row in rows:
                # Fill missing columns with empty strings
                complete_row = {col: row.get(col, '') for col in all_columns}
                # If propertyType is missing or empty, infer from source_folder
                if not complete_row.get('propertyType', '').strip():
                    if source_folder == 'Apartments':
                        complete_row['propertyType'] = "{'id': '1', 'nombre': 'Apartamento'}"
                    elif source_folder == 'Houses':
                        complete_row['propertyType'] = "{'id': '2', 'nombre': 'Casa'}"
                    elif source_folder == 'Offices':
                        complete_row['propertyType'] = "{'id': '3', 'nombre': 'Oficina'}"
                writer.writerow(complete_row)
                total_rows += 1
    
    print(f"\nSuccessfully combined {total_rows} rows into {output_file}")

if __name__ == '__main__':
    combine_csv_files()