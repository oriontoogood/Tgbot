# ─────────────────────────────────────────────
#  CONFIGURATION — fill in your values here
# ─────────────────────────────────────────────

# 1. Your bot token from @BotFather
BOT_TOKEN = "8578896479:AAG4HNsWksmuovgJKMscAh9nAm2d8vihoCg"

# 2. Your Telegram channel ID where results are forwarded
#    Example: "-1003860738398"
FORWARD_CHAT_ID = "-1004478546845"

# 3. User filtering (optional)
#    Add Telegram user IDs as numbers, e.g. [123456789, 987654321]
#    If ALLOWED_USERS is not empty, ONLY those users can message the bot
ALLOWED_USERS = []
BLOCKED_USERS = []

# 4. File paths — no need to change these
import os
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_FILE    = os.path.join(BASE_DIR, "data", "messages.db")
LOG_FILE   = os.path.join(BASE_DIR, "data", "messages.log")
MEDIA_DIR  = os.path.join(BASE_DIR, "media")

# ── Helius API (Solana blockchain) ────────────────────────────────────────────
HELIUS_API_KEY = "e0133e22-1e34-4a35-8597-b0949596972e"
HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=e0133e22-1e34-4a35-8597-b0949596972e"
