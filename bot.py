import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import httpx # Nodig om webhook te deleten

load_dotenv()

# --- JOUW NIEUWE GEGEVENS ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8237622987:AAGceFNdp0d2-q4FXlSx63gvO1YkF_b5LCY")
API_ID = int(os.getenv("API_ID", "37835956"))
API_HASH = os.getenv("API_HASH", "05685bc34698f8150a2f21cb1c463911")

# Initialiseer de client en py-tgcalls
bot_client = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
call_py = PyTgCalls(bot_client)

# --- NATIVE PYROGRAM COMMANDO HANDLER ---
@bot_client.on_message(filters.command("play"))
async def play_command(client, message: Message):
    print(f"==== ONTVANGEN COMMANDO: {message.text} van {message.from_user.first_name} ====")
    chat_id = message.chat.id
    query = message.text.replace("/play", "").strip()
    
    if not query:
        await message.reply("⚠️ Gebruik: `/play [naam van het nummer]`")
        return
    
    status_msg = await message.reply(f"🔍 Zoeken naar **{query}**...")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'ignoreerrors': True,
        }
        audio_url = None
        title = "Onbekend nummer"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"scsearch5:{query}", download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    if entry is not None and entry.get('url'):
                        audio_url = entry['url']
                        title = entry.get('title', 'Onbekend nummer')
                        break
                        
        if not audio_url:
            await status_msg.edit_text("❌ Geen bruikbare, onbeveiligde stream gevonden.")
            return
        
        # Start direct in de Voice Chat op dezelfde event loop!
        await call_py.play(
            chat_id,
            MediaStream(audio_url)
        )
        
        await status_msg.edit_text(f"🎶 Nu live te horen in de Voice Chat: **{title}**!")

    except Exception as e:
        print(f"FOUT IN VOICE CHAT: {str(e)}")
        await status_msg.edit_text(f"❌ Fout bij opstarten in Voice Chat: {str(e)}")


# --- DE LUS-MAGIE: START BOT BINNEN FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("==== STARTEN PYROGRAM & VOICE CHAT IN LUS ====")
    # Verwijder oude webhook om zeker te zijn van polling
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        print("==== Oude webhook verwijderd ====")
    except Exception as e:
        print(f"Kon webhook niet verwijderen (niet erg): {e}")

    # Start de bot en voice chat clients direct op de juiste event-loop
    await bot_client.start()
    await call_py.start()
    print("==== PYROGRAM BOT & VOICE DJ IS READY! ====")
    yield
    # Netjes stoppen bij afsluiten
    await bot_client.stop()
    print("==== Bot gestopt ====")

# Maak de FastAPI app aan met de lifespan
app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Voice Chat is online and free!"}