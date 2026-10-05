import requests
import datetime
from web3 import Web3

# ---------------------------------------------------------
# CHAIN-SPECIFIC CONFIGURATION & RPC FAILOVER POOLS
# ---------------------------------------------------------
CHAINS_CONFIG = {
    "solana": {
        "type": "solana",
        "rpc_list": [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana",
            "https://solana-mainnet.rpc.extrnode.com"
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

SWAP_EVENT_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"


def _fetch_solana(rpc_url, address, start_ts, end_ts):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [address, {"limit": 100}]
    }
    res = requests.post(rpc_url, json=payload, timeout=10)
    if res.status_code != 200:
        raise Exception(f"HTTP {res.status_code} Error")
    
    sigs = res.json().get("result", [])
    makers = set()
    for sig in sigs:
        block_time = sig.get("blockTime", 0)
        if start_ts <= block_time <= end_ts:
            makers.add(sig.get("signature"))
    return list(makers)


def _fetch_evm(rpc_url, address, start_block, end_block):
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
    if not w3.is_connected():
        raise Exception("Node connection failed")
        
    filter_params = {
        "fromBlock": hex(int(start_block)),
        "toBlock": hex(int(end_block)),
        "address": Web3.to_checksum_address(address),
        "topics": [SWAP_EVENT_TOPIC]
    }
    logs = w3.eth.get_logs(filter_params)
    makers = set()
    for log in logs:
        tx = w3.eth.get_transaction(log['transactionHash'])
        makers.add(tx['from'])
    return list(makers)


def extract_makers_with_failover(chain, address, start_val, end_val):
    chain = chain.lower()
    config = CHAINS_CONFIG[chain]
    rpc_pool = config["rpc_list"]
    
    status_logs = []
    
    for index, rpc in enumerate(rpc_pool, start=1):
        try:
            status_logs.append(f"Attempting {chain.upper()} endpoint #{index}: `{rpc}`")
            if config["type"] == "solana":
                makers = _fetch_solana(rpc, address, start_val, end_val)
            else:
                makers = _fetch_evm(rpc, address, start_val, end_val)
                
            status_logs.append(f"✅ **Success!** Found {len(makers)} makers.")
            return makers, status_logs
        except Exception as e:
            status_logs.append(f"⚠️ **Failed on endpoint #{index}:** {e}")
            
    status_logs.append("❌ All failover endpoints exhausted.")
    return [], status_logs
