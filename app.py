import streamlit as st
import pandas as pd
import json

# Import your functions here
from data_fun import (
    get_top_holders_other_tokens,
    get_unique_tokens_with_prices_and_symbols,
    combine_holders_with_prices
)

# Streamlit App
st.title("Token Holders and Price Dashboard")
st.sidebar.header("Input Parameters")

# Input parameters
token_mint_address = st.sidebar.text_input("Token Mint Address", placeholder="Enter token mint address")
top_n = st.sidebar.number_input("Number of Top Holders", min_value=10, value=20, step=1)
ignore_list = st.sidebar.text_area("Ignore List (Comma-separated)", placeholder="Enter wallet addresses to ignore")
min_dollar_value = st.sidebar.number_input("Minimum Dollar Value", min_value=10, value=100, step=10)

if st.sidebar.button("Fetch and Process Data"):
    if not token_mint_address:
        st.error("Please enter a valid token mint address.")
    else:
        # Process ignore list
        ignore_list = [addr.strip() for addr in ignore_list.split(",") if addr.strip()]

        # Fetch top holders' data
        st.info("Fetching top holders...")
        holders_data = get_top_holders_other_tokens(token_mint_address, top_n, ignore_list=ignore_list)

        if holders_data:
            st.success(f"Fetched data for {len(holders_data)} holders.")

            # Fetch unique token prices
            st.info("Fetching token prices...")
            token_prices = get_unique_tokens_with_prices_and_symbols(holders_data)
            st.success("Fetched token prices and symbols.")

            # Combine data
            st.info("Combining holders data with token prices...")
            combined_data = combine_holders_with_prices(holders_data, token_prices)
            st.success("Data combined successfully!")

            # Filter and display combined data
            st.subheader("Wallet Holdings (Filtered by Dollar Value)")

            for holder in combined_data:
                # Filter holdings for this holder
                filtered_holdings = [
                    {
                        "Token Address": token['token_address'],
                        "Amount": token['token_amount'],
                        "Symbol": token['symbol'],
                        "Price (USD)": token['priceUsd'],
                        "Dollar Value": round(token['dollar_value'], 2) if token['dollar_value'] else None
                    }
                    for token in holder['token_holdings']
                    if token['dollar_value'] and token['dollar_value'] >= min_dollar_value
                ]

                if filtered_holdings:
                    st.subheader(f"Wallet: {holder['owner_wallet']}")
                    df = pd.DataFrame(filtered_holdings)
                    st.table(df)  # Display as table

            # Save combined data to file
            st.download_button(
                label="Download Combined Data as JSON",
                data=json.dumps(combined_data, indent=4),
                file_name="holders_token_values.json",
                mime="application/json"
            )
        else:
            st.error("No data fetched for the given token mint address.")
