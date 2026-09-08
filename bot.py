import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pyrogram import Client, filters
from pytgcalls import PyTgCalls

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Maak een webserver aan voor de gratis Render-poort
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Anon Music Bot is online!"}

# Telegram bot client
bot = Client(
    "AnonMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(bot)

# Start-commando voor de bot
@bot.on_message(filters.command("start"))
async def start_commando(client, message):
    await message.reply_text("🤖 Vibe on! De gratis Anon Music Bot is wakker en klaar voor actie!")

# Start de Telegram-motor zodra de webserver opstart
@app.on_event("startup")
async def startup_event():
    await bot.start()
    # await call_py.start()
    print("Telegram bot succesvol gestart!")