import requests
import datetime
from web3 import Web3

# ---------------------------------------------------------
# CHAIN-SPECIFIC CONFIGURATION
# ---------------------------------------------------------
CHAINS_CONFIG = {
    "solana": {
        "type": "solana",
        "rpc_list": [
            "https://api.dexscreener.com/latest/dex/tokens/"
        ]
    },
    "bnb": {
        "type": "evm",
        "rpc_list": [
            "https://bsc-dataseed.binance.org/",
            "https://bsc-dataseed1.defibit.io/",
            "https://rpc.ankr.com/bsc"
        ]
    },
    "robinhood": {
        "type": "evm",
        "rpc_list": [
            "https://rpc.mainnet.chain.robinhood.com",
            "https://drpc.org/chainlist/robinhood-rpc"
        ]
    }
}

# Standard ERC-20 Transfer Event Signature
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _fetch_solana(api_url, address, start_ts, end_ts):
    """
    Fetches Solana market data and maker details using DexScreener API
    without needing raw node RPC calls.
    """
    url = f"{api_url}{address}"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    
    if res.status_code != 200:
        raise Exception(f"DEX Screener HTTP {res.status_code} Error")
        
    data = res.json()
    pairs = data.get("pairs", [])
    
    if not pairs:
        return []
        
    makers = set()
    
    for pair in pairs:
        # Collect Pair/Pool Address
        pair_address = pair.get("pairAddress")
        if pair_address:
            makers.add(pair_address)
            
        # Collect DEX routing contracts / factory if present
        dex_id = pair.get("dexId")
        if dex_id:
            makers.add(f"DEX: {dex_id}")
            
    return list(makers)


def _fetch_evm(rpc_url, address, start_block, end_block):
    """
    Fetches EVM transfer logs for chains like Robinhood & BNB.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
    if not w3.is_connected():
        raise Exception("Node connection failed")
        
    filter_params = {
        "fromBlock": hex(int(start_block)),
        "toBlock": hex(int(end_block)),
        "address": Web3.to_checksum_address(address),
        "topics": [TRANSFER_EVENT_TOPIC]
    }
    
    logs = w3.eth.get_logs(filter_params)
    makers = set()
    
    for log in logs:
        if len(log['topics']) >= 3:
            raw_to_address = log['topics'][2].hex()
            recipient = Web3.to_checksum_address("0x" + raw_to_address[-40:])
            makers.add(recipient)
            
    return list(makers)


def extract_makers_with_failover(chain, address, start_val, end_val):
    chain = chain.lower()
    config = CHAINS_CONFIG.get(chain, CHAINS_CONFIG["solana"])
    rpc_pool = config["rpc_list"]
    
    status_logs = []
    
    for index, endpoint in enumerate(rpc_pool, start=1):
        try:
            status_logs.append(f"Attempting {chain.upper()} endpoint #{index}: `{endpoint}`")
            
            if config["type"] == "solana":
                makers = _fetch_solana(endpoint, address, start_val, end_val)
            else:
                makers = _fetch_evm(endpoint, address, start_val, end_val)
                
            status_logs.append(f"✅ **Success!** Found {len(makers)} makers / pool entities.")
            return makers, status_logs
        except Exception as e:
            status_logs.append(f"⚠️ **Failed on endpoint #{index}:** {e}")
            
    status_logs.append("❌ All endpoints failed.")
    return [], status_logs
