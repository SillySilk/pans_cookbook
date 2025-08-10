#!/usr/bin/env python3
"""
Clean CSV file by fixing duplicate IDs and data issues
"""
import pandas as pd

def clean_herbs_csv():
    """Clean the herbs CSV file"""
    df = pd.read_csv('herbs.csv')
    print(f"Original CSV: {len(df)} rows, {df['id'].nunique()} unique IDs")
    
    # Remove duplicates, keeping the last occurrence (which might be more complete)
    df_clean = df.drop_duplicates(subset=['id'], keep='last')
    print(f"After removing ID duplicates: {len(df_clean)} rows")
    
    # Reset IDs to be sequential starting from 1
    df_clean = df_clean.sort_values('name')  # Sort by name first
    df_clean['id'] = range(1, len(df_clean) + 1)  # Reassign sequential IDs
    
    # Save backup of original
    df.to_csv('herbs_backup.csv', index=False)
    print("Backup saved as herbs_backup.csv")
    
    # Save cleaned version
    df_clean.to_csv('herbs.csv', index=False)
    print(f"Cleaned CSV saved: {len(df_clean)} herbs with sequential IDs")
    
    # Show first few cleaned records
    print("\nFirst 10 cleaned herbs:")
    for _, row in df_clean.head(10).iterrows():
        print(f"  ID {row['id']}: {row['name']}")

if __name__ == "__main__":
    clean_herbs_csv()