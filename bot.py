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
    await bot_client.start()
    await call_py.start()
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    async with httpx.AsyncClient() as client:
        await client.get(url)
    print("==== WEBHOOK & VOICE DJ IS READY! ====")
    yield

app = FastAPI(lifespan=lifespan)

bot_client = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
call_py = PyTgCalls(bot_client)

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Voice Chat Webhook is online!"}

def get_audio_url(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'ignoreerrors': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"scsearch5:{query}", download=False)
        if 'entries' in info:
            for entry in info['entries']:
                if entry is not None and 'url' in entry:
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
                
                await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"🔍 Zoeken naar **{query}**..."
                })
                
                try:
                    audio_url, title = get_audio_url(query)
                    
                    def run_in_loop():
                        asyncio.run(call_py.play(chat_id, MediaStream(audio_url)))

                    await asyncio.to_thread(run_in_loop)
                    
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