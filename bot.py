import os
import logging
import asyncio
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

ADMINS = [1849178309, 8286480139]

REQUIRED_CHANNELS = [
    "Cric_Fantast07",
    "Htr_Edits",
    "Paisa_Looterss",
    "KaalBomber"
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

if not MONGO_URI:
    logging.error("MONGO_URI is missing!")
    client = None
    db = None
    users = None
else:
    client = MongoClient(MONGO_URI)
    db = client["telegram_bot"]
    users = db["users"]

user_state = {}

def get_user_doc(uid):
    if users is None: return {}
    doc = users.find_one({"user_id": uid})
    if doc is None:
        doc = {
            "user_id": uid,
            "points": 0,
            "referrals": 0,
            "referred_by": None,
            "last_bonus": None,
            "joined_at": datetime.utcnow()
        }
        users.insert_one(doc)
    return doc

async def is_joined_all(uid, context):
    for ch in REQUIRED_CHANNELS:
        try:
            mem = await context.bot.get_chat_member(f"@{ch}", uid)
            if mem.status in ("left", "kicked"):
                return False
        except:
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if context.args and users is not None:
        try:
            raw = context.args[0]
            if "ref_" in raw:
                ref_id = int(raw.replace("ref_", ""))
            else:
                ref_id = int(raw)
                
            if ref_id != uid:
                ref_exists = users.find_one({"user_id": ref_id})
                user_exists = users.find_one({"user_id": uid})
                
                if ref_exists and not user_exists:
                    users.update_one({"user_id": ref_id}, {"$inc": {"points": 1, "referrals": 1}})
                    users.insert_one({
                        "user_id": uid,
                        "points": 0,
                        "referrals": 0,
                        "referred_by": ref_id,
                        "last_bonus": None,
                        "joined_at": datetime.utcnow()
                    })
        except Exception as e:
            logging.error(f"Referral Error: {e}")

    if users is not None:
        get_user_doc(uid)

    if not await is_joined_all(uid, context):
        btns = []
        for i in range(0, len(REQUIRED_CHANNELS), 2):
            row = []
            row.append(InlineKeyboardButton(f"JOIN {REQUIRED_CHANNELS[i]}", url=f"https://t.me/{REQUIRED_CHANNELS[i]}"))
            if i + 1 < len(REQUIRED_CHANNELS):
                row.append(InlineKeyboardButton(f"JOIN {REQUIRED_CHANNELS[i+1]}", url=f"https://t.me/{REQUIRED_CHANNELS[i+1]}"))
            btns.append(row)
        btns.append([InlineKeyboardButton("✅ VERIFY JOINED", callback_data="verify")])
        
        await update.message.reply_text(
            "⚠️ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗝𝗼𝗶𝗻 𝗔𝗹𝗹 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗧𝗼 𝗨𝘀𝗲 𝗧𝗵𝗶𝘀 𝗕𝗼𝘁 ⚠️.",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    menu = [
        [InlineKeyboardButton("💣 Start Bombing", callback_data="bomb")],
        [
            InlineKeyboardButton("➕ Refer / Invite", callback_data="refer"),
            InlineKeyboardButton("👤 My Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton("🔍 Buy Points", callback_data="buy_points"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")
        ]
    ]

    if uid in ADMINS:
        menu.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin")])

    await update.message.reply_text(
        "𝗞𝗮𝗮𝗹 𝗕𝗼𝗺𝗯𝗲𝗿 🇮🇳\n\n"
        "⚠️𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗧𝗼 𝗞𝗮𝗮𝗹 𝗕𝗼𝗺𝗯𝗲𝗿 🇮🇳\n"
        "⚠️𝗡𝗼𝘁𝗲 - 𝗘𝗻𝘁𝗲𝗿 10 𝗗𝗶𝗴𝗶𝘁 𝗡𝘂𝗺𝗯𝗲𝗿 𝗢𝗻𝗹𝘆\n"
        "📥 𝗘𝗻𝘁𝗲𝗿 𝗧𝗮𝗿𝗴𝗲𝘁 𝗡𝘂𝗺𝗯𝗲𝗿 -->",
        reply_markup=InlineKeyboardMarkup(menu)
    )

async def stats_cmd(update, context):
    if users is None: return
    d = get_user_doc(update.effective_user.id)
    await update.message.reply_text(
        f"Points: {d.get('points',0)}\nReferrals: {d.get('referrals',0)}\nReferred By: {d.get('referred_by')}"
    )

async def credits_cmd(update, context):
    if users is None: return
    d = get_user_doc(update.effective_user.id)
    await update.message.reply_text(f"Your Points: {d.get('points',0)}")

async def refer_cmd(update, context):
    user = update.effective_user
    bot = await context.bot.get_me()
    await update.message.reply_text(
        f"Your referral link:\nhttps://t.me/{bot.username}?start=ref_{user.id}"
    )

async def top_referrers(update, context):
    if users is None: return
    top = users.find().sort("referrals", -1).limit(10)
    msg = "🏆 Top Referrers:\n\n"
    for i, u in enumerate(top):
        msg += f"{i+1}. {u.get('user_id')} → {u.get('referrals',0)}\n"
    await update.message.reply_text(msg)

async def on_callback(update: Update, context):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "verify":
        if await is_joined_all(uid, context):
            await q.message.reply_text("✅ Verified!")
            await start(update, context)
        else:
            await q.message.reply_text("❌ You have not joined all channels yet.")
        return

    if q.data == "bomb":
        user_state[uid] = "awaiting_number"
        await q.edit_message_text("Enter a 10-digit number:")
        return

    if q.data == "refer":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{uid}"
        await q.message.reply_text(f"Your referral link:\n{link}")
        return

    if q.data == "stats":
        d = get_user_doc(uid)
        await q.message.reply_text(
            f"Points: {d.get('points',0)}\nReferrals: {d.get('referrals',0)}\nReferred By: {d.get('referred_by')}"
        )
        return

    if q.data == "bonus":
        d = get_user_doc(uid)
        last = d.get("last_bonus")
        now = datetime.utcnow()
        if last and (now - last) < timedelta(hours=24):
            rest = timedelta(hours=24) - (now - last)
            await q.edit_message_text(
                f"⛔ Come back after {rest.seconds//3600}h {(rest.seconds%3600)//60}m"
            )
            return
        if users:
            users.update_one({"user_id": uid}, {"$inc": {"points": 2}, "$set": {"last_bonus": now}})
        await q.edit_message_text("🎁 You received 2 points!")
        return

    if q.data == "admin":
        if uid not in ADMINS:
            await q.edit_message_text("❌ You are not admin.")
            return
        await q.edit_message_text(
            "🔧 Admin Commands:\n"
            "/addcredits <uid> <points>\n"
            "/setpoints <uid> <points>\n"
            "/broadcast <message>"
        )
        return

    if q.data == "buy_points":
        await q.message.reply_text(
            "Minimum Point 100 Buy\nContact @Undefeatable_Vikash77\n\n"
            "100 point → 100₹\n"
            "250 point → 200₹\n"
            "500 point → 400₹\n\n"
            "Only Serious Buyers, Not Timepassers."
        )
        return

async def on_message(update, context):
    uid = update.effective_user.id
    if not update.message or not update.message.text:
        return
    msg = update.message.text.strip()

    if user_state.get(uid) == "awaiting_number":
        if not msg.isdigit() or len(msg) != 10:
            await update.message.reply_text("❌ Enter a valid 10-digit number")
            return
        user_state[uid] = None
        
        status_msg = await update.message.reply_text(f"💣 Bombing started on {msg}")

        for p in ("10%", "35%", "60%", "90%", "100%"):
            await asyncio.sleep(2)
            try:
                await status_msg.edit_text(f"💣 Bombing started on {msg}\n💥 Progress: {p}")
            except:
                pass

        await update.message.reply_text("🔥 Bombing Completed!")
        return

async def addcredits(update, context):
    if update.effective_user.id not in ADMINS or users is None: return
    try:
        uid = int(context.args[0])
        pts = int(context.args[1])
        users.update_one({"user_id": uid}, {"$inc": {"points": pts}})
        await update.message.reply_text("Done.")
    except:
        await update.message.reply_text("Usage: /addcredits uid points")

async def setpoints(update, context):
    if update.effective_user.id not in ADMINS or users is None: return
    try:
        uid = int(context.args[0])
        pts = int(context.args[1])
        users.update_one({"user_id": uid}, {"$set": {"points": pts}})
        await update.message.reply_text("Updated.")
    except:
        await update.message.reply_text("Usage: /setpoints uid points")

async def broadcast(update, context):
    if update.effective_user.id not in ADMINS or users is None: return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast <text>")
        return
    sent = 0
    await update.message.reply_text("Broadcasting...")
    for u in users.find({}, {"user_id": 1}):
        try:
            await context.bot.send_message(u["user_id"], msg)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await update.message.reply_text(f"Sent to {sent} users")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing.")

    keep_alive()

    if BOT_TOKEN:
        bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("stats", stats_cmd))
        bot_app.add_handler(CommandHandler("credits", credits_cmd))
        bot_app.add_handler(CommandHandler("refer", refer_cmd))
        bot_app.add_handler(CommandHandler("top", top_referrers))
        bot_app.add_handler(CommandHandler("addcredits", addcredits))
        bot_app.add_handler(CommandHandler("setpoints", setpoints))
        bot_app.add_handler(CommandHandler("broadcast", broadcast))

        bot_app.add_handler(CallbackQueryHandler(on_callback))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

        print("Bot is starting...")
        bot_app.run_polling(drop_pending_updates=True)