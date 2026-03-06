
import pandas as pd
import os

def debug_data_loading():
    file_path = os.path.join('data', 'QQQ.csv')
    print(f"Loading {file_path}...")
    
    try:
        df = pd.read_csv(file_path)
        print("\nData Types:")
        print(df.dtypes)
        
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Mimic BaseStrategy date parsing
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
        if df['Date'].isna().any():
             df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        print("\nData Types after date parsing:")
        print(df.dtypes)
        
        # Check if we can calculate EMA on High/Low
        print("\nAttempting EMA calculation...")
        try:
            short_bull = df['High'].ewm(span=25, adjust=False).mean()
            print("EMA(High, 25) calculated successfully.")
            print(short_bull.tail())
        except Exception as e:
            print(f"EMA(High, 25) failed: {e}")
            
        try:
            short_bear = df['Low'].ewm(span=25, adjust=False).mean()
            print("EMA(Low, 25) calculated successfully.")
        except Exception as e:
            print(f"EMA(Low, 25) failed: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_data_loading()
