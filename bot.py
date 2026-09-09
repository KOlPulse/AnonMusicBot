import os
import asyncio
import httpx
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = 38561709
API_HASH = "45cb3c0d9a016faa268a269245e6fe4e"

from contextlib import asynccontextmanager

app = FastAPI()

# Pyrogram Client en PyTgCalls op dezelfde event-loop
bot_client = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
call_py = PyTgCalls(bot_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verwijder de oude webhook bij Telegram zodat de bot weer normaal kan luisteren
    async with httpx.AsyncClient() as client:
        await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        
    await bot_client.start()
    await call_py.start()
    print("==== PYROGRAM BOT & VOICE DJ IS READY! ====")
    yield
    await bot_client.stop()

app.router.lifespan_context = lifespan

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Voice Chat is online!"}

# --- NATIV# --- NATIVE PYROGRAM COMMANDO HANDLER ---
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