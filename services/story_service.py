import os
import json
import logging
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("dugtrio.story")

# Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
STORY_PROTOCOL_ENABLED = bool(PRIVATE_KEY and RPC_URL)

w3 = None
account = None
ip_asset_contract = None

# Initialize Web3 Connection
if STORY_PROTOCOL_ENABLED:
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        account = w3.eth.account.from_key(PRIVATE_KEY)
        
        IP_ASSET_REGISTRY_ADDRESS = "0x77319B4031e6eF1250907aa00018B8B1c67a244b" 

        # Path to the ABI file relative to this script
        abi_path = os.path.join(os.path.dirname(__file__), "ip_asset_registry_abi.json")
        if os.path.exists(abi_path):
            with open(abi_path) as f:
                IP_ASSET_REGISTRY_ABI = json.load(f)
            
            ip_asset_contract = w3.eth.contract(address=IP_ASSET_REGISTRY_ADDRESS, abi=IP_ASSET_REGISTRY_ABI)
            logger.info("✅ Story Protocol: Connected and Contract Loaded.")
        else:
            logger.warning(f"⚠️ Story Protocol: ABI file not found at {abi_path}.")
            STORY_PROTOCOL_ENABLED = False
            
    except Exception as e:
        logger.error(f"❌ Story Protocol Error: {e}")
        STORY_PROTOCOL_ENABLED = False
else:
    logger.warning("🟡 Story Protocol: Disabled (Missing Keys)")

async def register_ip_on_chain(project_tag: str, report_data: dict) -> str:
    """Handles the blockchain transaction to register IP."""
    if not STORY_PROTOCOL_ENABLED or not ip_asset_contract:
        raise Exception("Story Protocol is not enabled.")

    ip_name = f"DugTrio Sentiment: ${project_tag.upper()} - {report_data['timestamp']}"
    content_uri = f"data:application/json,{json.dumps(report_data)}"
    
    tx = ip_asset_contract.functions.register(
        0, # policyId
        ip_name,
        w3.keccak(text=content_uri),
        content_uri
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    
    if hasattr(signed_tx, "rawTransaction"):
        raw_tx = signed_tx.rawTransaction
    elif hasattr(signed_tx, "raw_transaction"):
        raw_tx = signed_tx.raw_transaction
    else:
        raw_tx = signed_tx["rawTransaction"]

    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    # Normalize tx hex
    try:
        tx_hex = tx_hash.hex()
    except Exception:
        try:
            tx_hex = Web3.toHex(tx_hash)
        except Exception:
            tx_hex = str(tx_hash)

    # Attempt to wait for receipt, but do not fail the whole flow if it remains pending.
    try:
        # Wait up to 5 minutes for the tx to be mined; if not mined, return tx hash so caller
        # can display the pending transaction and let the explorer handle it.
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        logger.info(f"✅ Transaction mined: {tx_hex}")
    except Exception as e:
        logger.warning(f"⏳ Transaction not mined within timeout: {e} - returning tx hash anyway.")

    return tx_hex