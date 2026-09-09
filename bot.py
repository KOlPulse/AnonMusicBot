import os
import httpx
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

# Vul hier straks jouw eigen Telegram User ID in! (Bijv: [123456789, 987654321])
ADMIN_IDS = [] 

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Webhook is online and ready!"}

@app.on_event("startup")
async def startup_event():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    async with httpx.AsyncClient() as client:
        await client.get(url)
    print("==== WEBHOOK SERVER IS READY FOR ACTION! ====")

@app.post("/webhook")
async def receive_update(request: Request):
    data = await request.json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")
        user_name = message["from"].get("first_name", "Friend")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            if text.startswith("/play"):
                
                # --- VIP ADMIN CHECK ---
                if ADMIN_IDS and user_id not in ADMIN_IDS:
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "⛔ Access Denied: This bot is reserved for administrators."
                    })
                    return {"status": "ok"}

                query = text.replace("/play", "").strip()
                if not query:
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "⚠️ Usage: /play [artist or title]"
                    })
                    return {"status": "ok"}
                
                await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"🔍 Smart searching SoundCloud for: '{query}'..."
                })
                
                try:
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': 'downloads/%(id)s.%(ext)s',
                        'noplaylist': True,
                        'max_filesize': 50000000,
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    os.makedirs("downloads", exist_ok=True)
                    file_path = None
                    title = None
                    author = None
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # Zoek de top 5 resultaten (download nog niets)
                        info = ydl.extract_info(f"scsearch5:{query}", download=False)
                        
                        if not info or 'entries' not in info or not info['entries']:
                            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"❌ Could not find any tracks for '{query}'."
                            })
                            return {"status": "ok"}
                            
                        # Loop door de 5 resultaten om de DRM beveiliging te omzeilen
                        for entry in info['entries']:
                            try:
                                # Probeer dit specifieke nummer te downloaden
                                dl_info = ydl.extract_info(entry['url'], download=True)
                                file_path = ydl.prepare_filename(dl_info)
                                title = dl_info.get('title', query)
                                author = dl_info.get('uploader', 'Unknown Artist')
                                break # Gelukt! Breek direct uit de loop.
                            except Exception as e:
                                print(f"Skipping track due to error (likely DRM): {e}")
                                continue # Error of DRM slot? Geen paniek, we proberen de volgende in de lijst!
                                
                    if not file_path or not os.path.exists(file_path):
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Found tracks, but all were DRM protected or unavailable."
                        })
                        return {"status": "ok"}
                        
                    # Succes! Stuur het bestand als echte audiospeler
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Found an unlocked track! Uploading {title}..."
                    })
                    
                    with open(file_path, "rb") as audio_file:
                        files = {"audio": audio_file}
                        data_payload = {
                            "chat_id": chat_id,
                            "title": title,
                            "performer": author,
                            "caption": f"🎵 {title} - {author}"
                        }
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio",
                            data=data_payload,
                            files=files,
                            timeout=120.0
                        )
                        
                    # Ruim de server netjes op
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An unexpected error occurred during the search process."
                    })
                    
    return {"status": "ok"}