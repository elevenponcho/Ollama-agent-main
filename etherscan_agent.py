#
# Etherscan + Ollama + IPFS Support+ LangChain Agent
#
# Tools included:
#   - get_latest_block
#   - get_latest_block_details
#   - get_latest_block_gas_used
#   - get_gas_price
#   - get_eth_balance
#   - get_tx_count (nonce)
#   - get_normal_tx_list (recent normal txs for an address)
#   - get_internal_tx_list (recent internal txs)
#   - get_erc20_token_balance (address + token contract)
#   - get_erc20_token_transfers (address + token contract)
#   - get_tx_status (success/fail)
#   - get_tx_info (basic transaction info)
#
# The LangChain agent can answer a wide range of natural-language questions
# about Ethereum mainnet using these tools.

import requests
from typing import Any, Dict, List, Union
from ipfs_integration import IPFSUploader

from langchain_community.llms import Ollama
from langchain.tools import Tool
# from langchain.agents import initialize_agent, AgentType

# 🔑 Put YOUR real Etherscan API key here
ETHERSCAN_API_KEY = ""

ETHERSCAN_BASE_V1 = "https://api.etherscan.io/api"
ETHERSCAN_BASE_V2 = "https://api.etherscan.io/v2/api"


# -------------------------
# LLM SETUP (Ollama + Mistral)
# -------------------------

def create_llm():
    """
    Create an Ollama LLM object pointing to the local llama3.2:3b model.
    """
    llm = Ollama(
        model="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0,
        num_predict=256,
        timeout=60,
    )
    return llm


def ask_llm(prompt: str) -> str:
    """
    Simple helper to query the bare LLM with no tools.
    """
    llm = create_llm()
    return llm.invoke(prompt)


# -------------------------
# Helper utilities
# -------------------------

def _check_api_key() -> Union[None, str]:
    if not ETHERSCAN_API_KEY or "PASTE_YOUR" in ETHERSCAN_API_KEY:
        return "ERROR: ETHERSCAN_API_KEY is not set. Please edit etherscan_agent.py."
    return None


def _clean_address(address: str) -> str:
    addr = (
        address.strip()
        .replace("'", "")
        .replace('"', "")
        .split()[0]  # take first token if LLM adds extra words
        .split(",")[0]
        .strip()
    )
    return addr


def _is_valid_eth_address(address: str) -> bool:
    return address.startswith("0x") and len(address) == 42


def _shorten_hash(h: str, length: int = 10) -> str:
    if not h or len(h) <= length:
        return h
    return f"{h[:6]}...{h[-4:]}"


# -------------------------
# ETHERSCAN RAW FUNCTIONS
# -------------------------

def get_latest_block_number() -> Union[int, str]:
    """
    Latest block number (proxy.eth_blockNumber).
    """
    err = _check_api_key()
    if err:
        return err

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=proxy"
        "&action=eth_blockNumber"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "result" in data:
            hex_block = data["result"]
            try:
                return int(hex_block, 16)
            except Exception as e:
                return f"ERROR converting hex block {hex_block}: {e}"

        return f"Unexpected Etherscan response: {data}"

    except Exception as e:
        return f"Exception calling Etherscan: {e}"


def get_latest_block_details() -> Union[Dict[str, Any], str]:
    """
    Details for latest block (proxy.eth_getBlockByNumber with tag=latest).
    Returns dict with keys: block_number, miner, tx_count, gas_used.
    """
    err = _check_api_key()
    if err:
        return err

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=proxy"
        "&action=eth_getBlockByNumber"
        "&tag=latest"
        "&boolean=true"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        block = data.get("result")
        if not block:
            return f"Unexpected Etherscan response for block details: {data}"

        miner = block.get("miner")
        txs = block.get("transactions", [])
        tx_count = len(txs)
        gas_used_hex = block.get("gasUsed")
        number_hex = block.get("number")

        try:
            number = int(number_hex, 16) if number_hex else None
        except Exception:
            number = number_hex

        try:
            gas_used = int(gas_used_hex, 16) if gas_used_hex else None
        except Exception:
            gas_used = gas_used_hex

        return {
            "block_number": number,
            "miner": miner,
            "tx_count": tx_count,
            "gas_used": gas_used,
        }

    except Exception as e:
        return f"Exception calling Etherscan for block details: {e}"


def get_latest_block_gas_used() -> str:
    """
    Convenience helper: just gas used of latest block.
    """
    details = get_latest_block_details()
    if isinstance(details, dict):
        return str(details.get("gas_used"))
    return str(details)


def get_gas_price() -> str:
    """
    Current gas price (proxy.eth_gasPrice) in wei + gwei.
    """
    err = _check_api_key()
    if err:
        return err

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=proxy"
        "&action=eth_gasPrice"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "result" in data:
            hex_price = data["result"]
            try:
                wei = int(hex_price, 16)
                gwei = wei / 1e9
                return f"{wei} wei ({gwei:.2f} gwei)"
            except Exception as e:
                return f"ERROR converting gas price {hex_price}: {e}"

        return f"Unexpected Etherscan response for gas price: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for gas price: {e}"


def get_eth_balance(address: str) -> Union[float, str]:
    """
    ETH balance for an address (in ETH).
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=account"
        "&action=balance"
        f"&address={addr}"
        "&tag=latest"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "result" in data:
            wei_str = data["result"]
            try:
                wei_int = int(wei_str)
                eth_balance = wei_int / 1e18
                return eth_balance
            except Exception as e:
                return f"ERROR converting wei amount {wei_str}: {e}"

        return f"Unexpected Etherscan response for balance: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for balance: {e}"


def get_tx_count(address: str) -> Union[int, str]:
    """
    Transaction count / nonce for an address (proxy.eth_getTransactionCount).
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=proxy"
        "&action=eth_getTransactionCount"
        f"&address={addr}"
        "&tag=latest"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "result" in data:
            hex_nonce = data["result"]
            try:
                return int(hex_nonce, 16)
            except Exception as e:
                return f"ERROR converting nonce {hex_nonce}: {e}"

        return f"Unexpected Etherscan response for tx count: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for tx count: {e}"


def get_normal_tx_list(address: str, max_txs: int = 5) -> Union[str, List[Dict[str, Any]]]:
    """
    Recent normal (external) transactions for an address.
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"

    url = (
        f"{ETHERSCAN_BASE_V1}"
        "?module=account"
        "&action=txlist"
        f"&address={addr}"
        "&startblock=0"
        "&endblock=99999999"
        "&page=1"
        f"&offset={max_txs}"
        "&sort=desc"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        if status == "1":
            return data.get("result", [])
        elif status == "0" and data.get("message") == "No transactions found":
            return []
        return f"Unexpected Etherscan response for normal tx list: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for normal tx list: {e}"


def get_internal_tx_list(address: str, max_txs: int = 5) -> Union[str, List[Dict[str, Any]]]:
    """
    Recent internal transactions for an address.
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"

    url = (
        f"{ETHERSCAN_BASE_V1}"
        "?module=account"
        "&action=txlistinternal"
        f"&address={addr}"
        "&startblock=0"
        "&endblock=99999999"
        "&page=1"
        f"&offset={max_txs}"
        "&sort=desc"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        if status == "1":
            return data.get("result", [])
        elif status == "0" and data.get("message") == "No transactions found":
            return []
        return f"Unexpected Etherscan response for internal tx list: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for internal tx list: {e}"


def get_erc20_token_balance(address: str, contract: str) -> Union[float, str]:
    """
    ERC20 token balance for an address + token contract.
    Returns balance in "natural" units assuming 18 decimals (approx).
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    contract_addr = _clean_address(contract)

    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"
    if not _is_valid_eth_address(contract_addr):
        return f"ERROR: Invalid token contract address: {contract_addr}"

    url = (
        f"{ETHERSCAN_BASE_V1}"
        "?module=account"
        "&action=tokenbalance"
        f"&contractaddress={contract_addr}"
        f"&address={addr}"
        "&tag=latest"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "result" in data:
            raw = data["result"]
            try:
                value_int = int(raw)
                # assume 18 decimals by default (most ERC20)
                return value_int / 1e18
            except Exception as e:
                return f"ERROR converting token balance {raw}: {e}"

        return f"Unexpected Etherscan response for token balance: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for token balance: {e}"


def get_erc20_token_transfers(address: str, contract: str, max_txs: int = 5) -> Union[str, List[Dict[str, Any]]]:
    """
    Recent ERC20 token transfers for an address + contract.
    """
    err = _check_api_key()
    if err:
        return err

    addr = _clean_address(address)
    contract_addr = _clean_address(contract)

    if not _is_valid_eth_address(addr):
        return f"ERROR: Invalid Ethereum address: {addr}"
    if not _is_valid_eth_address(contract_addr):
        return f"ERROR: Invalid token contract address: {contract_addr}"

    url = (
        f"{ETHERSCAN_BASE_V1}"
        "?module=account"
        "&action=tokentx"
        f"&contractaddress={contract_addr}"
        f"&address={addr}"
        "&page=1"
        f"&offset={max_txs}"
        "&startblock=0"
        "&endblock=99999999"
        "&sort=desc"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        if status == "1":
            return data.get("result", [])
        elif status == "0" and data.get("message") == "No transactions found":
            return []
        return f"Unexpected Etherscan response for token transfers: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for token transfers: {e}"


def get_tx_status(tx_hash: str) -> str:
    """
    Get transaction success/fail status.
    """
    err = _check_api_key()
    if err:
        return err

    h = tx_hash.strip().split()[0].split(",")[0].strip()

    url = (
        f"{ETHERSCAN_BASE_V1}"
        "?module=transaction"
        "&action=gettxreceiptstatus"
        f"&txhash={h}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status")
        result = data.get("result", {})
        if status == "1" and "status" in result:
            return "Success" if result["status"] == "1" else "Failed"
        return f"Unexpected Etherscan response for tx status: {data}"

    except Exception as e:
        return f"Exception calling Etherscan for tx status: {e}"


def get_tx_info(tx_hash: str) -> Union[Dict[str, Any], str]:
    """
    Basic transaction info via proxy.eth_getTransactionByHash.
    """
    err = _check_api_key()
    if err:
        return err

    h = tx_hash.strip().split()[0].split(",")[0].strip()

    url = (
        f"{ETHERSCAN_BASE_V2}"
        "?chainid=1"
        "&module=proxy"
        "&action=eth_getTransactionByHash"
        f"&txhash={h}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        tx = data.get("result")
        if not tx:
            return f"Unexpected Etherscan response for tx info: {data}"

        # Return only a subset of fields to keep it compact
        return {
            "hash": tx.get("hash"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value": tx.get("value"),  # in hex wei
            "nonce": tx.get("nonce"),
            "gas": tx.get("gas"),
            "gasPrice": tx.get("gasPrice"),
            "blockNumber": tx.get("blockNumber"),
        }

    except Exception as e:
        return f"Exception calling Etherscan for tx info: {e}"


# -------------------------
# LANGCHAIN TOOLS + AGENT
# -------------------------

def create_etherscan_tools() -> List[Tool]:
    """
    Wrap Python functions as LangChain Tools so the agent can call them.
    """

    # --- Tool wrappers return strings (more LLM-friendly) ---

    def tool_latest_block(_input: str = "") -> str:
        result = get_latest_block_number()
        return str(result)

    def tool_latest_block_details(_input: str = "") -> str:
        result = get_latest_block_details()
        if isinstance(result, dict):
            return (
                f"Latest block number: {result.get('block_number')}\n"
                f"Miner address: {result.get('miner')}\n"
                f"Transaction count: {result.get('tx_count')}\n"
                f"Gas used: {result.get('gas_used')}"
            )
        return str(result)

    def tool_latest_block_gas_used(_input: str = "") -> str:
        return get_latest_block_gas_used()

    def tool_gas_price(_input: str = "") -> str:
        return get_gas_price()

    def tool_eth_balance(address: str) -> str:
        result = get_eth_balance(address)
        if isinstance(result, float):
            return f"{result:.6f} ETH"
        return str(result)

    def tool_tx_count(address: str) -> str:
        result = get_tx_count(address)
        return str(result)

    def tool_normal_tx_list(address: str) -> str:
        txs = get_normal_tx_list(address, max_txs=5)
        if isinstance(txs, str):
            return txs
        if not txs:
            return "No recent normal transactions found."
        lines = []
        for tx in txs:
            lines.append(
                f"{_shorten_hash(tx.get('hash'))} | "
                f"from={_shorten_hash(tx.get('from'))} -> "
                f"to={_shorten_hash(tx.get('to'))} | "
                f"value={tx.get('value')} wei"
            )
        return "\n".join(lines)

    def tool_internal_tx_list(address: str) -> str:
        txs = get_internal_tx_list(address, max_txs=5)
        if isinstance(txs, str):
            return txs
        if not txs:
            return "No recent internal transactions found."
        lines = []
        for tx in txs:
            lines.append(
                f"{_shorten_hash(tx.get('hash'))} | "
                f"from={_shorten_hash(tx.get('from'))} -> "
                f"to={_shorten_hash(tx.get('to'))} | "
                f"value={tx.get('value')} wei"
            )
        return "\n".join(lines)

    def tool_erc20_token_balance(input_str: str) -> str:
        """
        Input should be: 'address, token_contract_address'
        """
        parts = [p.strip() for p in input_str.split(",")]
        if len(parts) != 2:
            return (
                "ERROR: Input must be 'address, token_contract_address' "
                "(comma-separated)."
            )
        balance = get_erc20_token_balance(parts[0], parts[1])
        if isinstance(balance, float):
            return f"{balance:.6f} (assuming 18 decimals)"
        return str(balance)

    def tool_erc20_token_transfers(input_str: str) -> str:
        """
        Input should be: 'address, token_contract_address'
        """
        parts = [p.strip() for p in input_str.split(",")]
        if len(parts) != 2:
            return (
                "ERROR: Input must be 'address, token_contract_address' "
                "(comma-separated)."
            )
        txs = get_erc20_token_transfers(parts[0], parts[1], max_txs=5)
        if isinstance(txs, str):
            return txs
        if not txs:
            return "No recent ERC20 transfers found for that address/token."
        lines = []
        for tx in txs:
            lines.append(
                f"{_shorten_hash(tx.get('hash'))} | "
                f"from={_shorten_hash(tx.get('from'))} -> "
                f"to={_shorten_hash(tx.get('to'))} | "
                f"value={tx.get('value')} (raw token units)"
            )
        return "\n".join(lines)

    def tool_tx_status(tx_hash: str) -> str:
        return get_tx_status(tx_hash)

    def tool_tx_info(tx_hash: str) -> str:
        info = get_tx_info(tx_hash)
        if isinstance(info, str):
            return info
        return (
            f"hash={_shorten_hash(info.get('hash'))}\n"
            f"from={info.get('from')}\n"
            f"to={info.get('to')}\n"
            f"value={info.get('value')} wei (hex)\n"
            f"nonce={info.get('nonce')}\n"
            f"gas={info.get('gas')}\n"
            f"gasPrice={info.get('gasPrice')} wei (hex)\n"
            f"blockNumber={info.get('blockNumber')}"
        )

    tools = [
        Tool(
            name="get_latest_block",
            func=tool_latest_block,
            description=(
                "Get the latest Ethereum block number. "
                "Input should be an empty string."
            ),
        ),
        Tool(
            name="get_latest_block_details",
            func=tool_latest_block_details,
            description=(
                "Get details about the latest Ethereum block: block number, miner "
                "address, transaction count, and gas used. Input should be empty."
            ),
        ),
        Tool(
            name="get_latest_block_gas_used",
            func=tool_latest_block_gas_used,
            description=(
                "Get only the gas used in the latest Ethereum block. "
                "Input should be empty."
            ),
        ),
        Tool(
            name="get_gas_price",
            func=tool_gas_price,
            description=(
                "Get the current gas price on Ethereum mainnet, in wei and gwei. "
                "Input should be empty."
            ),
        ),
        Tool(
            name="get_eth_balance",
            func=tool_eth_balance,
            description=(
                "Get the Ether balance of an address. "
                "Input must be the Ethereum address string in hex (starting with 0x)."
            ),
        ),
        Tool(
            name="get_tx_count",
            func=tool_tx_count,
            description=(
                "Get the transaction count (nonce) for an address. "
                "Input must be the Ethereum address string in hex (starting with 0x)."
            ),
        ),
        Tool(
            name="get_normal_tx_list",
            func=tool_normal_tx_list,
            description=(
                "Get up to 5 most recent normal (external) transactions for an "
                "address. Input must be the Ethereum address string."
            ),
        ),
        Tool(
            name="get_internal_tx_list",
            func=tool_internal_tx_list,
            description=(
                "Get up to 5 most recent internal transactions for an address. "
                "Input must be the Ethereum address string."
            ),
        ),
        Tool(
            name="get_erc20_token_balance",
            func=tool_erc20_token_balance,
            description=(
                "Get the ERC20 token balance for an address and token contract. "
                "Input must be 'address, token_contract_address' (comma-separated)."
            ),
        ),
        Tool(
            name="get_erc20_token_transfers",
            func=tool_erc20_token_transfers,
            description=(
                "Get up to 5 recent ERC20 token transfers for an address+token. "
                "Input must be 'address, token_contract_address' (comma-separated)."
            ),
        ),
        Tool(
            name="get_tx_status",
            func=tool_tx_status,
            description=(
                "Get whether a transaction was Success or Failed. "
                "Input must be the transaction hash."
            ),
        ),
        Tool(
            name="get_tx_info",
            func=tool_tx_info,
            description=(
                "Get basic info about a transaction: from, to, value, gas, "
                "gasPrice, blockNumber, etc. Input must be the transaction hash."
            ),
        ),
    ]

    return tools


# def create_etherscan_agent(verbose: bool = True):
#     """
#     Create a LangChain ReAct agent wired to all Etherscan tools.
#     """
#     llm = create_llm()
#     tools = create_etherscan_tools()

#     # Small system-style prompt via the 'input' prefix when we call.
#     # (We also tell the agent how to behave in ask_etherscan_agent.)
#     agent = initialize_agent(
#         tools=tools,
#         llm=llm,
#         agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#         verbose=verbose,
#         handle_parsing_errors=True,
#         max_iterations=3,
#         early_stopping_method="generate",
#     )
#     return agent


# def ask_etherscan_agent(question: str) -> str:
#     """
#     Ask a natural-language question; the agent chooses which tools to call.
#     """
#     agent = create_etherscan_agent(verbose=False)
#     prompt = (
#         "You are an Ethereum on-chain analyst. You have access to several tools "
#         "that read live data from Etherscan for Ethereum mainnet.\n\n"
#         "ALWAYS use the tools when the question is about real blockchain data, "
#         "addresses, blocks, transactions, balances, gas, or tokens.\n\n"
#         "If a question cannot be answered with the available tools, respond "
#         "honestly that you do not have the required data.\n\n"
#         f"User question: {question}"
#     )
#     result = agent.invoke({"input": prompt})
#     return result.get("output", str(result))
def ask_etherscan_agent(question: str) -> dict:
    """
    Fast deterministic tool dispatcher.
    Also stores execution in BlockShareCloud (IPFS + block) via HTTP.
    Returns:
        dict with keys: "answer", "ipfs_cid" (or None if upload failed)
    """

    import time
    import requests

    ipfs_cid = None
    answer = ""
    tool_name = ""
    tool_output = ""

    llm = create_llm()
    tools = {tool.name: tool for tool in create_etherscan_tools()}

    routing_prompt = f"""
You are an Ethereum assistant.

Select the correct tool for this question.

Available tools:
{", ".join(tools.keys())}

Return ONLY the tool name.

Question: {question}
"""

    tool_name = llm.invoke(routing_prompt).strip()

    # If no valid tool selected
    if tool_name not in tools:
        answer = "I can only answer Ethereum on-chain questions."

        payload = {
            "question": question,
            "tool_name": "none",
            "tool_input": "",
            "tool_output": "",
            "final_answer": answer,
            "timestamp": time.time(),
        }

        try:
            from ipfs_integration import IPFSUploader
            uploader = IPFSUploader()
            ipfs_cid = uploader.upload_execution_log(payload, append_to_history=True)
    
            if ipfs_cid:
                print(f"Stored in IPFS: CID = {ipfs_cid}")
                print(f"View link: https://ipfs.io/ipfs/{ipfs_cid}")
            else:
                print("Warning: IPFS upload failed. Data not persisted.")
        
        except Exception as e:
            print(f"IPFS Integration Error: {e}")

        return {"answer": answer, "ipfs_cid": ipfs_cid}


    # Tool execution
    tool_input = ""
    tool_output = tools[tool_name].func(tool_input)
    answer = tool_output

    # Store in BlockShareCloud
    payload = {
        "question": question,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "final_answer": answer,
        "timestamp": time.time(),
    }

    try:
        from ipfs_integration import IPFSUploader
        uploader = IPFSUploader()
        ipfs_cid = uploader.upload_execution_log(payload, append_to_history=True)
    
        if ipfs_cid:
            print(f"Stored in BlockShareCloud (IPFS): CID = {ipfs_cid}")
            print(f"View link: https://ipfs.io/ipfs/{ipfs_cid}")
        else:
            print("Warning: IPFS upload failed. Data not persisted.")
        
    except Exception as e:
        print(f"IPFS Integration Error: {e}")

    return {"answer": answer, "ipfs_cid": ipfs_cid}

