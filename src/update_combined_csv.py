#!/usr/bin/env python3
"""
Script to update the combined CSV file by appending new CSV files from the data/ subdirectories.
Keeps track of processed files to avoid reprocessing.
"""

import os
import csv
from pathlib import Path

def update_combined_csv():
    data_dir = Path('data')
    combined_file = Path('data/combined_listings.csv')
    processed_file = Path('data/processed_files.txt')
    
    # Read processed files list
    processed = set()
    if processed_file.exists():
        with open(processed_file, 'r') as f:
            for line in f:
                processed.add(line.strip())
    
    # Find all CSV files in data/ subdirectories
    csv_files = list(data_dir.glob('*/*.csv'))
    print(f"Found {len(csv_files)} CSV files in total")
    
    new_files = []
    for csv_file in csv_files:
        # Get the relative path from data_dir
        rel_path = csv_file.relative_to(data_dir)
        if str(rel_path) not in processed:
            new_files.append((csv_file, rel_path))
    
    print(f"Found {len(new_files)} new CSV files to process")
    
    if not new_files:
        print("No new files to process.")
        return
    
    # Process each new file
    for csv_file, rel_path in new_files:
        print(f"Processing {rel_path}")
        # Determine if we need to write header
        write_header = not combined_file.exists()
        
        # Open the combined file in append mode
        with open(combined_file, 'a', newline='', encoding='utf-8') as outfile:
            # Read the new CSV file
            with open(csv_file, 'r', encoding='utf-8') as infile:
                reader = csv.reader(infile)
                header = next(reader)  # read the header
                if write_header:
                    # Write the header to the combined file
                    writer = csv.writer(outfile)
                    writer.writerow(header)
                # Write the rest of the rows
                writer = csv.writer(outfile)
                for row in reader:
                    writer.writerow(row)
        
        # Mark this file as processed
        processed.add(str(rel_path))
    
    # Update the processed files list
    with open(processed_file, 'w') as f:
        for rel_path in sorted(processed):
            f.write(rel_path + '\n')
    
    print(f"Updated combined CSV: {combined_file}")
    print(f"Updated processed files list: {processed_file}")

if __name__ == '__main__':
    update_combined_csv()