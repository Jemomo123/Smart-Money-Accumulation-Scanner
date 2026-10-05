import streamlit as st
import datetime
from fetcher import extract_makers_with_failover

st.set_page_config(page_title="Accumulation Zone Scanner", page_icon="🎯", layout="centered")

st.title("🎯 Smart Money Accumulation Scanner")
st.write("Extract buyer wallet addresses during historical consolidation zones across Solana, BNB, and Robinhood chain.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Scan Parameters")
chain = st.sidebar.selectbox("Select Network", ["Solana", "BNB", "Robinhood"])
token_address = st.sidebar.text_input("Contract / Pair Address")

st.sidebar.markdown("---")

if chain.lower() == "solana":
    st.subheader("Solana Timeframe Setup")
    date_input = st.date_input("Consolidation Date", datetime.date(2026, 9, 27))
    start_time = st.time_input("Start Time (UTC)", datetime.time(7, 0))
    end_time = st.time_input("End Time (UTC)", datetime.time(15, 0))
    
    # Convert inputs to Unix Timestamps
    start_dt = datetime.datetime.combine(date_input, start_time, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime.combine(date_input, end_time, tzinfo=datetime.timezone.utc)
    
    start_val = int(start_dt.timestamp())
    end_val = int(end_dt.timestamp())
else:
    st.subheader("EVM Block Range Setup")
    start_val = st.number_input("Start Block", value=32000000, step=1)
    end_val = st.number_input("End Block", value=32000500, step=1)

# --- SCAN TRIGGER ---
if st.button("Extract Accumulation Makers", type="primary"):
    if not token_address.strip():
        st.warning("Please enter a valid Contract or Pair address in the sidebar.")
    else:
        with st.spinner("Executing multi-chain failover scan..."):
            makers, logs = extract_makers_with_failover(chain, token_address.strip(), start_val, end_val)
            
            # Execution Logs
            with st.expander("RPC Failover Logs", expanded=True):
                for log in logs:
                    st.write(log)
            
            # Results Output
            if makers:
                st.success(f"Successfully Extracted {len(makers)} Unique Buyers!")
                st.dataframe({"Wallet / Signature Addresses": makers}, use_container_width=True)
                
                # Copy/Paste Output
                st.subheader("Copyable Address List")
                st.text_area("Wallets (One per line)", value="\n".join(makers), height=200)
            else:
                st.error("No makers found or all network endpoints timed out.")
  
