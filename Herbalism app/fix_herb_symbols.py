#!/usr/bin/env python3
"""
Quick script to add default symbols to herbs missing them
"""
import pandas as pd

# Default herb symbol for missing entries
DEFAULT_SYMBOL = "🌿"

def fix_herb_symbols():
    df = pd.read_csv('herbs.csv')
    
    print(f"Before: {len(df[df['symbol'].isna() | (df['symbol'] == '')])} herbs missing symbols")
    
    # Fill empty or NaN symbols with default
    df['symbol'] = df['symbol'].fillna(DEFAULT_SYMBOL)
    df.loc[df['symbol'] == '', 'symbol'] = DEFAULT_SYMBOL
    
    # Save back
    df.to_csv('herbs.csv', index=False)
    
    print(f"After: {len(df[df['symbol'].isna() | (df['symbol'] == '')])} herbs missing symbols")
    print("Fixed! All herbs now have symbols.")

if __name__ == "__main__":
    fix_herb_symbols()