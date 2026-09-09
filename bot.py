import os
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp

# Vaste API gegevens en bot token uit de omgeving of direct ingevuld
API_ID = 38561709
API_HASH = "45cb3c0d9a016faa268a269245e6fe4e"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# 1. Start de Pyrogram Userbot/Bot client voor audio streaming
app = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(app)

# Helper functie om YouTube audio te downloaden of stream-link op te halen
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

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        "👋 Welcome to **AnonMusicBot**!\n\n"
        "Use `/play [search term]` to stream music directly into the Voice Chat and catch the vibe!"
    )

@app.on_message(filters.command("play"))
async def play_handler(client, message):
    # Controleer of er een zoekterm is meegeleverd
    if len(message.command) < 2:
        await message.reply_text("⚠️ Gebruik: `/play [naam van het nummer]`")
        return

    query = " ".join(message.command[1:])
    chat_id = message.chat.id
    
    status_msg = await message.reply_text(f"🔍 Zoeken naar **{query}**...")

    try:
        # Zoek het nummer via yt-dlp
        audio_url, title = await asyncio.to_thread(get_audio_url, query)
        
        await status_msg.edit_text(f"🎵 Verbinden met de Voice Chat voor: **{title}**...")

        # Start de stream in de Voice Chat van de groep
        await call_py.join_group_call(
            chat_id,
            AudioPiped(audio_url)
        )
        
        await status_msg.edit_text(f"🎶 Nu live te horen in de Voice Chat: **{title}**!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Er is een fout opgetreden: {str(e)}")

# Start de applicatie
async def main():
    await app.start()
    await call_py.start()
    print("Bot en Voice Chat DJ draaien succesvol!")
    await asyncio.gather(
        app.idle(),
        call_py.idle()
    )

if __name__ == "__main__":
    asyncio.run(main())