import os
import asyncio
import httpx
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = 38561709
API_HASH = "45cb3c0d9a016faa268a269245e6fe4e"
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup acties
    await bot_client.start()
    await call_py.start()
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    async with httpx.AsyncClient() as client:
        await client.get(url)
    print("==== WEBHOOK & VOICE DJ IS READY! ====")
    yield
    # Shutdown acties (optioneel)

app = FastAPI(lifespan=lifespan)

bot_client = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
call_py = PyTgCalls(bot_client)

def get_audio_url(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'ignoreerrors': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Zoek gelijk naar de eerste 5 opties om een vrije track te vinden
        info = ydl.extract_info(f"scsearch5:{query}", download=False)
        if 'entries' in info:
            for entry in info['entries']:
                if entry is not None and 'url' in entry:
                    # Sla DRM-beveiligde of lege streams over
                    if entry.get('url'):
                        return entry['url'], entry.get('title', 'Onbekend nummer')
        raise Exception("Geen bruikbare, onbeveiligde stream gevonden.")

@app.post("/webhook")
async def receive_update(request: Request):
    data = await request.json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            if text.startswith("/play"):
                query = text.replace("/play", "").strip()
                
                if not query:
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "⚠️ Gebruik: `/play [naam van het nummer]`"
                    })
                    return {"status": "ok"}
                
                status_msg_res = await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"🔍 Zoeken naar **{query}**..."
                })
                
                try:
                    # Haal direct de stream URL op van YouTube via een achtergrond-thread
                    audio_url, title = await asyncio.to_thread(get_audio_url, query)
                    
                    # Bel in bij de Voice Chat van deze groep!
                    await call_py.play(
                        chat_id,
                        MediaStream(audio_url)
                    )
                    
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"🎶 Nu live te horen in de Voice Chat: **{title}**!"
                    })

                except Exception as e:
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ Fout bij opstarten in Voice Chat: {str(e)}"
                    })
                    
    return {"status": "ok"}