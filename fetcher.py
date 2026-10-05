def _fetch_solana(rpc_url, address, start_ts, end_ts):
    # Step 1: Get signature list for the token account/pair
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
    valid_signatures = []
    
    for sig in sigs:
        block_time = sig.get("blockTime")
        # Filter signatures falling inside your UTC start/end timestamp window
        if block_time and (start_ts <= block_time <= end_ts):
            valid_signatures.append(sig.get("signature"))
            
    makers = set()
    
    # Step 2: Parse transactions to extract fee-payer / buyer wallet addresses
    for signature in valid_signatures[:20]: # Limit to top 20 to prevent RPC rate limits
        tx_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        tx_res = requests.post(rpc_url, json=tx_payload, timeout=10)
        if tx_res.status_code == 200:
            tx_data = tx_res.json().get("result")
            if tx_data and "transaction" in tx_data:
                account_keys = tx_data["transaction"]["message"]["accountKeys"]
                # The first account key in a Solana transaction is the fee payer (buyer/signer)
                for key in account_keys:
                    if isinstance(key, dict) and key.get("signer"):
                        makers.add(key.get("pubkey"))
                    elif isinstance(key, str) and account_keys.index(key) == 0:
                        makers.add(key)
                        
    return list(makers)
