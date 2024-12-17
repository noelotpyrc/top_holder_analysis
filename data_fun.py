import requests
import json
import base64
import struct

with open('config.json', 'r') as file:
    config = json.load(file)

RPC_ENDPOINT = config['SOL_RPC']

def decode_token_amount(data):
    """
    Decode the token amount from the account data.
    """
    # Decode base64 data
    decoded_data = base64.b64decode(data)
    
    # Extract token amount from the decoded binary data (fields in SPL Token layout)
    # SPL Token account layout:
    # https://docs.solana.com/developing/programming-model/transactions#account-layout
    token_amount = struct.unpack_from('<Q', decoded_data, offset=64)[0]
    return token_amount

def get_top_holders(token_mint_address, top_n):
    url = f"{RPC_ENDPOINT}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [token_mint_address]
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200 and response.json().get('result'):
        accounts = response.json()['result']['value']
        return accounts[:top_n]
    else:
        print(f"Error fetching top holders: {response.status_code}, {response.text}")
        return []

def get_wallet_owner_for_token_account(token_account):
    url = RPC_ENDPOINT
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [token_account, {"encoding": "jsonParsed"}]
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200 and response.json().get('result'):
        account_data = response.json()['result']['value']['data']['parsed']['info']
        return account_data.get('owner')
    else:
        print(f"Error fetching wallet owner for token account {token_account}: {response.status_code}, {response.text}")
        return None


def get_token_accounts_by_owner(owner_wallet):
    """
    Fetch all token accounts owned by a specific wallet and decode token balances, token addresses, and decimals.
    Excludes tokens with decimals = 0.

    Args:
        owner_wallet (str): The wallet address of the owner.

    Returns:
        list: A list of dictionaries containing token accounts, amounts, decimals, and associated token addresses.
    """
    if len(owner_wallet) != 44:  # Validate the wallet address length for Base58
        print(f"Invalid owner wallet address: {owner_wallet}")
        return []

    url = RPC_ENDPOINT
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            owner_wallet,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}  # Use jsonParsed to extract mint address and decimals
        ]
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200 and response.json().get('result'):
        token_accounts = response.json()['result']['value']
        decoded_accounts = []
        for account in token_accounts:
            account_info = account['account']['data']['parsed']['info']
            decimals = int(account_info['tokenAmount']['decimals'])  # Extract decimals

            # Skip tokens with decimals = 0
            if decimals == 0:
                continue

            token_amount = int(account_info['tokenAmount']['amount'])
            token_address = account_info['mint']  # Extract the mint address

            # Add account info to the decoded list
            decoded_accounts.append({
                "token_account": account['pubkey'],
                "token_amount": token_amount,
                "token_address": token_address,
                "decimals": decimals
            })
        return decoded_accounts
    else:
        print(f"Error fetching token accounts for wallet {owner_wallet}: {response.status_code}, {response.text}")
        return []


def get_token_data_from_dexscreener(token_address):
    """
    Fetch token data from the Dexscreener API.

    Args:
        token_address (str): The address of the token to query.

    Returns:
        dict: A dictionary containing the token data if successful, or an error message.
    """
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: Received status code {response.status_code}")
            return {"error": f"Unable to fetch data. Status code: {response.status_code}"}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}

import pandas as pd

def extract_price_and_liquidity(data):
    """
    Extract price and liquidity information from Dexscreener API response.

    Args:
        data (dict): The response JSON from Dexscreener API.

    Returns:
        pd.DataFrame: A DataFrame with price and liquidity data.
    """
    pairs = data.get('pairs', [])
    extracted_data = [
        {
            'chainId': pair['chainId'],
            'dexId': pair['dexId'],
            'priceUsd': float(pair['priceUsd']),
            'liquidityUsd': pair['liquidity']['usd'],
            'liquidityBase': pair['liquidity']['base'],
            'liquidityQuote': pair['liquidity']['quote']
        }
        for pair in pairs
    ]
    
    return max(
    [
        {
            'chainId': pair['chainId'],
            'dexId': pair['dexId'],
            'priceUsd': float(pair['priceUsd']),
            'liquidityUsd': pair['liquidity']['usd'],
            'liquidityBase': pair['liquidity']['base'],
            'liquidityQuote': pair['liquidity']['quote']
        }
        for pair in pairs
    ],
    key=lambda x: x['liquidityUsd']
)['priceUsd']

def get_token_data_from_dexscreener(token_address):
    """
    Fetch token data from the Dexscreener API.

    Args:
        token_address (str): The address of the token to query.

    Returns:
        dict: A dictionary containing the token data if successful, or an error message.
    """
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: Received status code {response.status_code}")
            return {"error": f"Unable to fetch data. Status code: {response.status_code}"}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}

import pandas as pd

def extract_price_and_liquidity(data):
    """
    Extract price and liquidity information from Dexscreener API response.

    Args:
        data (dict): The response JSON from Dexscreener API.

    Returns:
        dict: A dictionary with the token pair having the highest liquidity,
              including chainId, dexId, priceUsd, liquidityUsd, liquidityBase, liquidityQuote, and symbol.
    """
    pairs = data.get('pairs', [])
    if not pairs:
        print("No pairs found in data.")
        return None

    extracted_data = [
        {
            'chainId': pair['chainId'],
            'dexId': pair['dexId'],
            'priceUsd': float(pair['priceUsd']) if 'priceUsd' in pair else None,
            'liquidityUsd': pair['liquidity']['usd'],
            'liquidityBase': pair['liquidity']['base'],
            'liquidityQuote': pair['liquidity']['quote'],
            'symbol': pair['baseToken']['symbol'].strip()
        }
        for pair in pairs
        if pair.get('liquidity', {}).get('usd')  # Ensure liquidity is present
    ]

    if not extracted_data:
        print("No valid pairs with liquidity found.")
        return None

    return max(extracted_data, key=lambda x: x['liquidityUsd'])

def get_top_holders_other_tokens(token_mint_address, top_n, ignore_list=None):
    """
    Fetch top holders' other token holdings without fetching prices, with added print statements
    and an ignore list to skip specified holders.

    Args:
        token_mint_address (str): The mint address of the token.
        top_n (int): Number of top holders to fetch.
        ignore_list (list): List of holder account addresses to ignore.

    Returns:
        dict: A JSON object with top holders and their other token holdings.
    """
    if ignore_list is None:
        ignore_list = []

    print(f"Fetching top {top_n} holders for token: {token_mint_address}")
    top_holders = get_top_holders(token_mint_address, top_n)
    holders_data = []
    all_token_addresses = set()

    print(f"Retrieved {len(top_holders)} top holders.")

    for idx, holder in enumerate(top_holders, 1):
        holder_address = holder['address']

        if holder_address in ignore_list:
            print(f"Skipping holder {idx}/{len(top_holders)}: {holder_address} (ignored)")
            continue

        print(f"Processing holder {idx}/{len(top_holders)}: {holder_address}")
        token_account = holder_address
        owner_wallet = get_wallet_owner_for_token_account(token_account)

        if owner_wallet in ignore_list:
            print(f"Skipping holder {idx}/{len(top_holders)}: {owner_wallet} (ignored)")
            continue

        if not owner_wallet:
            print(f"Warning: Owner wallet not found for token account: {token_account}")
            continue

        print(f"Owner wallet resolved: {owner_wallet}")
        token_accounts = get_token_accounts_by_owner(owner_wallet)
        print(f"Found {len(token_accounts)} token accounts for wallet: {owner_wallet}")

        token_holdings = []

        for account in token_accounts:
            token_address = account['token_address']
            token_amount = account['token_amount'] / (10 ** account['decimals'])

            # Skip tokens with 0 amount
            if token_amount == 0:
                print(f"Skipping token with 0 amount: {token_address}")
                continue

            # Collect token addresses for price fetching outside this loop
            token_holdings.append({
                'token_address': token_address,
                'token_amount': token_amount
            })

        holders_data.append({
            'owner_wallet': owner_wallet,
            'token_holdings': token_holdings
        })

        print(f"Finished processing holder {idx}/{len(top_holders)}.")

    print("All holders processed. Returning results.")
    return holders_data

def get_unique_tokens_with_prices_and_symbols(holders_data):
    """
    Extract unique tokens from holders' data, fetch their prices and symbols.

    Args:
        holders_data (list): List of holder data with token holdings.

    Returns:
        dict: A dictionary mapping token addresses to their price and symbol.
    """
    unique_tokens = set()
    token_prices = {}

    # Collect unique token addresses
    for holder in holders_data:
        for token in holder['token_holdings']:
            unique_tokens.add(token['token_address'])

    print(f"Found {len(unique_tokens)} unique tokens.")

    # Fetch price and symbol for each unique token
    for idx, token_address in enumerate(unique_tokens, 1):
        # print(f"Fetching price and symbol for token {idx}/{len(unique_tokens)}: {token_address}")
        dex_data = get_token_data_from_dexscreener(token_address)
        print(dex_data)
        
        if dex_data and dex_data.get('pairs'):
            token_info = extract_price_and_liquidity(dex_data)
            token_prices[token_address] = {
                'priceUsd': token_info['priceUsd'],
                'symbol': token_info['symbol']
            }
        else:
            print(f"Error or no data for token: {token_address} (pairs: {dex_data.get('pairs') if dex_data else None})")
            token_prices[token_address] = {
                'priceUsd': None,
                'symbol': None
            }

    return token_prices

def combine_holders_with_prices(holders_data, token_prices, output_file="holders_token_values.json"):
    """
    Combine holders' token holdings with token prices to calculate dollar values.

    Args:
        holders_data (list): List of holders and their token holdings.
        token_prices (dict): Dictionary of token prices and symbols.
        output_file (str): File name to save the combined data as a JSON.

    Returns:
        dict: Combined data with token values in terms of USD and symbols.
    """
    combined_data = []

    for holder in holders_data:
        owner_wallet = holder["owner_wallet"]
        token_holdings = holder["token_holdings"]

        enriched_holdings = []
        for holding in token_holdings:
            token_address = holding["token_address"]
            token_amount = holding["token_amount"]

            # Get token price and symbol
            token_info = token_prices.get(token_address, {"priceUsd": None, "symbol": None})
            price_usd = token_info["priceUsd"]
            symbol = token_info["symbol"]

            # Calculate dollar value if price is available
            if price_usd is not None:
                dollar_value = token_amount * price_usd  # Assuming token amounts are in smallest units
            else:
                dollar_value = None

            enriched_holdings.append({
                "token_address": token_address,
                "token_amount": token_amount,
                "symbol": symbol,
                "priceUsd": price_usd,
                "dollar_value": dollar_value
            })

        combined_data.append({
            "owner_wallet": owner_wallet,
            "token_holdings": enriched_holdings
        })

    # Save to a JSON file
    with open(output_file, "w") as f:
        json.dump(combined_data, f, indent=4)

    return combined_data



