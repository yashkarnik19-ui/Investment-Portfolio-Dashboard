import streamlit as st
import pandas as pd
import numpy as np
import datetime
import altair as alt

# 1. DATA LOADING & CORE RECON LOGIC
@st.cache(allow_output_mutation=True)
def load_all_data():
    df = pd.read_csv("market_data_source_of_truth1.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    
    mapping_df = pd.read_csv("symbols_valid_meta.csv")
    common = set(df['s_uid'].unique()).intersection(set(mapping_df['Symbol'].unique()))
    df = df[df['s_uid'].isin(common)]
    mapping_df = mapping_df[mapping_df['Symbol'].isin(common)]
    
    # --- JUNIOR ANALYST SIMULATION LOGIC ---
    np.random.seed(42)
    # Price Simulation
    df['Internal_Price'] = df['Close'] * np.random.uniform(0.998, 1.002, len(df))
    df['Price_Diff'] = (df['Internal_Price'] - df['Close']).abs()
    
    # Define Status based on a simple $0.10 tolerance
    df['Status'] = df['Price_Diff'].apply(lambda x: 'MATCHED' if x <= 0.10 else 'PRICE_BREAK')
    
    # Assign Simple Reason Codes
    reasons = ['Price Variance', 'Buy/Sell Mismatch', 'Currency Difference']
    df['Break_Reason'] = df.apply(lambda x: np.random.choice(reasons) if x['Status'] == 'PRICE_BREAK' else 'N/A', axis=1)
    
    # Financial Impact (1,000 share lot)
    qty = 1000 
    df['VaR'] = df['Price_Diff'] * qty
    df['Market_Value'] = df['Close'] * qty
    df['Qty_Bought'] = qty
    
    return df, mapping_df

data, mapping = load_all_data()
name_to_sym = pd.Series(mapping['Symbol'].values, index=mapping['Security Name']).to_dict()
sym_to_name = pd.Series(mapping['Security Name'].values, index=mapping['Symbol']).to_dict()

# 2. SESSION STATE
if 'sel_sym' not in st.session_state:
    st.session_state.sel_sym = sorted(list(sym_to_name.keys()))[0]
if 'sel_name' not in st.session_state:
    st.session_state.sel_name = sym_to_name.get(st.session_state.sel_sym)

def on_name_change():
    st.session_state.sel_sym = name_to_sym[st.session_state.selected_name_widget]
    st.session_state.sel_name = st.session_state.selected_name_widget

def on_sym_change():
    st.session_state.sel_name = sym_to_name.get(st.session_state.selected_sym_widget)
    st.session_state.sel_sym = st.session_state.selected_sym_widget

# 3. SIDEBAR
st.sidebar.title("🛠️ TradeRecon Pro")
page = st.sidebar.radio("Navigation", ["Executive Overview", "Breakage Analysis"])
st.sidebar.markdown("---")

names_list, syms_list = sorted(list(name_to_sym.keys())), sorted(list(sym_to_name.keys()))
st.sidebar.selectbox("Security Name", options=names_list, index=names_list.index(st.session_state.sel_name), key='selected_name_widget', on_change=on_name_change)
st.sidebar.selectbox("Ticker Symbol", options=syms_list, index=syms_list.index(st.session_state.sel_sym), key='selected_sym_widget', on_change=on_sym_change)

date_range = st.sidebar.date_input("Date Range", value=(data['Date'].min().date(), data['Date'].max().date()))

# 4. FILTERING
ticker_df = data[data['s_uid'] == st.session_state.sel_sym].copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_ts, end_ts = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered_df = ticker_df[(ticker_df['Date'] >= start_ts) & (ticker_df['Date'] <= end_ts)]
    date_range_str = f"{date_range[0].strftime('%d-%m-%Y')} to {date_range[1].strftime('%d-%m-%Y')}"
else:
    filtered_df = ticker_df
    date_range_str = "Full History"

# --- PAGE 1: EXECUTIVE OVERVIEW ---
if page == "Executive Overview":
    st.title("📈 Executive Overview")
    st.markdown(f"**Security:** {st.session_state.sel_name} ({st.session_state.sel_sym})")
    st.info(f"📅 **Date range selected is:** {date_range_str}")
    
    total_trades = len(filtered_df)
    break_df = filtered_df[filtered_df['Status'] == 'PRICE_BREAK']
    avg_price = filtered_df['Close'].mean() if total_trades > 0 else 0
    
    # Row 1 Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Trades", f"{total_trades:,}")
    m2.metric("Break Count", len(break_df))
    m3.metric("Match Rate", f"{((total_trades-len(break_df))/total_trades*100 if total_trades > 0 else 0):.1f}%")

    # Row 2 Metrics
    m4, m5, m6 = st.columns(3)
    m4.metric("Avg Stock Price", f"${avg_price:.2f}")
    m5.metric("Total VaR", f"${filtered_df['VaR'].sum():,.2f}")
    m6.metric("Value in Breakage", f"${break_df['Market_Value'].sum():,.2f}")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Price Movement")
        if not filtered_df.empty:
            filtered_df['Date_Chart'] = pd.to_datetime(filtered_df['Date'])
            base = alt.Chart(filtered_df).encode(
                x=alt.X('Date_Chart:T', title='Date'),
                tooltip=[
                    alt.Tooltip('s_uid:N', title='Ticker'),
                    alt.Tooltip('Open:Q', title='Open Price', format='$.2f'),
                    alt.Tooltip('Close:Q', title='Closing Price', format='$.2f'),
                    alt.Tooltip('Qty_Bought:Q', title='Shares Traded')
                ]
            )
            l1 = base.mark_line(color='#f58518').encode(y=alt.Y('Open:Q', scale=alt.Scale(zero=False), title="Price ($)"))
            l2 = base.mark_line(color='#4c78a8').encode(y=alt.Y('Close:Q'))
            st.altair_chart(l1 + l2, use_container_width=True)

    with col_b:
        st.subheader("Breaks by Reason")
        if not break_df.empty:
            reason_counts = break_df.groupby('Break_Reason').size().reset_index(name='Count')
            bar = alt.Chart(reason_counts).mark_bar(color='#d62728', size=30).encode(
                x=alt.X('Break_Reason:N', title='Reason Code', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Count:Q', title='Number of Trades'),
                tooltip=['Break_Reason', 'Count']
            ).properties(height=300)
            st.altair_chart(bar, use_container_width=True)
        else:
            st.success("All trades matched! ✅")

# --- PAGE 2: BREAKAGE ANALYSIS ---
else:
    st.title("🔍 Breakage Analysis")
    st.markdown(f"**Security:** {st.session_state.sel_name} ({st.session_state.sel_sym})")
    st.info(f"📅 **Date range selected is:** {date_range_str}")
    
    exceptions = filtered_df[filtered_df['Status'] == 'PRICE_BREAK'].copy()
    if not exceptions.empty:
        st.error(f"Action Required: {len(exceptions)} breaks identified.")
        exceptions['Date_Display'] = exceptions['Date'].dt.strftime('%d-%m-%Y')
        
        # Simple, readable columns for a Junior Analyst
        st.dataframe(exceptions[['Date_Display', 'Break_Reason', 'Internal_Price', 'Close', 'Price_Diff', 'VaR']])
        
        st.download_button("📥 Export Break List", data=exceptions.to_csv(index=False), file_name=f"Recon_Report.csv")
    else:
        st.success("Ledger is clean. No breaks found. ✅")