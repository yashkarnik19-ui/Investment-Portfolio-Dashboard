```python
import os
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
folder_path = ''
save_path = ""
start_date, end_date = '2026-01-01', '2026-03-31'

# --- STAGE 1: HARVESTING & TIME-SHIFTING ---

all_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
selected_files = sorted(all_files)[:3000] 
master_list = []

for filename in selected_files:
    df = pd.read_csv(os.path.join(folder_path, filename))
    df['Date'] = pd.to_datetime(df['Date']) + pd.DateOffset(years=6)
    
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask].copy()
    filtered_df['s_uid'] = filename.replace('.csv', '')
    
    if not filtered_df.empty:
        master_list.append(filtered_df)

full_market_data = pd.concat(master_list, ignore_index=True)

# --- STAGE 2: INTENTIONAL ERROR GENERATION ---
# Creates realistic operational "Breaks" for the dashboard
np.random.seed(42)
final_data = full_market_data.copy()

# Initialize columns
final_data['Internal_Price'] = final_data['Close']
final_data['Status'] = 'MATCHED'
final_data['Break_Reason'] = 'N/A'

# Inject errors into 10% of the data
total_rows = len(final_data)
error_count = int(total_rows * 0.10)
error_indices = np.random.choice(final_data.index, size=error_count, replace=False)

# Define error categories
price_idx = error_indices[:int(error_count * 0.4)]      
currency_idx = error_indices[int(error_count * 0.4):int(error_count * 0.8)] 
buysell_idx = error_indices[int(error_count * 0.8):]    

# 1. Price Variance (Standard market data discrepancy)
final_data.loc[price_idx, 'Internal_Price'] += np.random.uniform(0.20, 1.50, size=len(price_idx))
final_data.loc[price_idx, 'Status'] = 'PRICE_BREAK'
final_data.loc[price_idx, 'Break_Reason'] = 'Price Variance'

# 2. Currency Difference (Simulates 1.1x FX conversion error)
final_data.loc[currency_idx, 'Internal_Price'] *= 1.10
final_data.loc[currency_idx, 'Status'] = 'PRICE_BREAK'
final_data.loc[currency_idx, 'Break_Reason'] = 'Currency Difference'

# 3. Buy/Sell Mismatch (Simulates a missing or reversed trade)
final_data.loc[buysell_idx, 'Internal_Price'] = 0.00 
final_data.loc[buysell_idx, 'Status'] = 'PRICE_BREAK'
final_data.loc[buysell_idx, 'Break_Reason'] = 'Buy/Sell Mismatch'

# --- STAGE 3: FINANCIAL IMPACT MATH ---
# Calculates VaR and Market Value for risk analysis
final_data['Price_Diff'] = (final_data['Internal_Price'] - final_data['Close']).abs()
qty = 1000
final_data['VaR'] = final_data['Price_Diff'] * qty
final_data['Market_Value'] = final_data['Close'] * qty
final_data['Qty_Bought'] = qty

# --- STAGE 4: SAVE MASTER FILE ---
# Saves the final CSV for the Streamlit App to consume
final_data.to_csv(save_path, index=False)

print(f"Process Complete! Master file saved as: {save_path}")
print(f"Operational Stats: {len(final_data)} total rows | {error_count} identified breaks.")
```

    Process Complete! Master file saved as: /Users/yashkarnik/Desktop/My Portfolio/Investment Portfolio Analysis/TradeReconApp/market_data_source_of_truth1.csv
    Operational Stats: 184267 total rows | 18426 identified breaks.

