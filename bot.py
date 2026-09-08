import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pyrogram import Client, filters

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot is online en gezond!"}

# Telegram bot client
bot = Client(
    "AnonMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

@bot.on_message()
async def alles_zien(client, message):
    print(f"🚨 ALERT: Bericht binnengekomen van {message.from_user.first_name if message.from_user else 'Onbekend'}: '{message.text}'")

@bot.on_message(filters.command("start"))
async def start_commando(client, message):
    print("🔔 Jaaa! Start commando gekregen op Telegram!")
    await message.reply_text("🤖 Vibe on! De gratis Anon Music Bot is wakker en klaar voor actie!")

@app.on_event("startup")
async def startup_event():
    print("==== Starten met verbinden naar Telegram... ====")
    await bot.start()
    
    # Registreer de commando's direct bij Telegram zodat ze blauw/klikbaar worden
    try:
        from pyrogram.types import BotCommand
        await bot.set_bot_commands([
            BotCommand("start", "Start de muziek bot en activeer de vibe"),
            BotCommand("play", "Speel een nummer af via YouTube")
        ])
    except Exception as e:
        print(f"Kon commando's niet registreren: {e}")
        
    print("==== TELEGRAM BOT LUISTERST APPARAAT IS ACTIEF! ====")

@app.on_event("shutdown")
async def shutdown_event():
    if bot.is_connected:
        await bot.stop()
    print("==== Bot netjes afgesloten ====")