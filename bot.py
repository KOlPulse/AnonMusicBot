import os
import asyncio
from fastapi import FastAPI
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import yt_dlp

API_ID = 38561709
API_HASH = "45cb3c0d9a016faa268a269245e6fe4e"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# 1. FastAPI Web Server (dit houdt Render online en groen)
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "De Music Bot en Web Server draaien succesvol!"}

# 2. De Pyrogram Telegram Bot
bot = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(bot)

def get_audio_url(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info.get('title', 'Onbekend nummer')

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        "👋 Welcome to **AnonMusicBot**!\n\n"
        "Use `/play [search term]` to stream music directly into the Voice Chat and catch the vibe!"
    )

@bot.on_message(filters.command("play"))
async def play_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Gebruik: `/play [naam van het nummer]`")
        return

    query = " ".join(message.command[1:])
    chat_id = message.chat.id
    
    status_msg = await message.reply_text(f"🔍 Zoeken naar **{query}**...")

    try:
        audio_url, title = await asyncio.to_thread(get_audio_url, query)
        await status_msg.edit_text(f"🎵 Verbinden met de Voice Chat voor: **{title}**...")

        await call_py.play(
            chat_id,
            MediaStream(audio_url)
        )
        
        await status_msg.edit_text(f"🎶 Nu live te horen in de Voice Chat: **{title}**!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Er is een fout opgetreden: {str(e)}")

# 3. Koppel de Bot aan de opstartprocedure van de Web Server
@app.on_event("startup")
async def startup_event():
    await bot.start()
    await call_py.start()
    print("Telegram Bot en Voice Chat DJ draaien nu in de achtergrond!")