import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pyrogram import Client, filters

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = FastAPI()

# 👇 DE REDDER IN NOOD: Nu accepteert de server de HEAD-inspectie van Render!
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot is online en gezond!"}

bot = Client(
    "AnonMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

@bot.on_message(filters.command("start"))
async def start_commando(client, message):
    print("🔔 Jaaa! Start commando gekregen op Telegram!")
    await message.reply_text("🤖 Vibe on! De gratis Anon Music Bot is wakker en klaar voor actie!")

@app.on_event("startup")
async def startup_event():
    print("==== Starten met verbinden... ====")
    await bot.start()
    print("==== TELEGRAM BOT IS SUCCESVOL GESTART ====")