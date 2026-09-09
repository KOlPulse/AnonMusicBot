import os
import httpx
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

# Vul hier straks jouw eigen Telegram User ID in! (Bijv: [123456789])
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
                        'ignoreerrors': True, # Skipt DRM-errors automatisch
                    }
                    
                    os.makedirs("downloads", exist_ok=True)
                    file_path = None
                    title = None
                    author = None
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"scsearch5:{query}", download=False)
                        
                        if not info or 'entries' not in info:
                            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"❌ Could not find any tracks for '{query}'."
                            })
                            return {"status": "ok"}
                            
                        for entry in info['entries']:
                            if entry is None:
                                continue
                                
                            # Forceer de echte naam vanuit de zoekopdracht
                            current_title = entry.get('title', query)
                            current_author = entry.get('uploader', 'Unknown Artist')
                                
                            try:
                                dl_info = ydl.extract_info(entry['url'], download=True)
                                if not dl_info:
                                    continue
                                    
                                file_path = ydl.prepare_filename(dl_info)
                                title = current_title
                                author = current_author
                                break # Gevonden!
                            except Exception as inner_e:
                                print(f"Skipping track due to inner error: {inner_e}")
                                continue
                                
                    if not file_path or not os.path.exists(file_path):
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Found tracks, but all were DRM protected or unavailable."
                        })
                        return {"status": "ok"}
                        
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Found track! Uploading {title}..."
                    })
                    
                    # --- DE FIX VOOR DE NAAM EN DE 00:00 TIJD ---
                    with open(file_path, "rb") as audio_file:
                        # Door het bestand als een specifieke .mp3 string mee te geven, dwingen we 
                        # Telegram om de 00:00 fout te negeren en de metadata perfect te lezen!
                        files = {"audio": (f"{title} - {author}.mp3", audio_file, "audio/mpeg")}
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
                        
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    error_msg = str(e)
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ TECHNISCHE FOUT: {error_msg}"
                    })
                    
    return {"status": "ok"}