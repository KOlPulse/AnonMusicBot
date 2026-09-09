import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

# 1. Vul hier straks jouw eigen Telegram User ID in! (Bijv: [123456789, 987654321])
# Laat de lijst leeg [] om iedereen tijdelijk toegang te geven.
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
                    "text": f"🔍 Searching music database for: '{query}'..."
                })
                
                try:
                    # --- VERCEL API MIRRORS (Geen IP Blokkades) ---
                    mirrors = [
                        "https://jiosaavn-api-privatecvc2.vercel.app",
                        "https://saavn-api-v3.vercel.app",
                        "https://jiosaavn-api-ten-eta.vercel.app"
                    ]
                    
                    best_audio_url, title, author = None, None, None
                    
                    for mirror in mirrors:
                        try:
                            res = await client.get(f"{mirror}/search/songs?query={query}", timeout=10.0)
                            if res.status_code == 200:
                                api_data = res.json()
                                results = []
                                
                                # Check beide veelvoorkomende JSON architecturen van deze API
                                if isinstance(api_data, dict) and "data" in api_data:
                                    if isinstance(api_data["data"], dict) and "results" in api_data["data"]:
                                        results = api_data["data"]["results"]
                                    elif isinstance(api_data["data"], list):
                                        results = api_data["data"]
                                        
                                if results:
                                    song = results[0]
                                    title = song.get("name", query).replace("&quot;", '"')
                                    author = song.get("primaryArtists", "Unknown Artist")
                                    downloads = song.get("downloadUrl", [])
                                    
                                    if downloads:
                                        best_audio_url = downloads[-1]["url"]
                                        break # Gevonden! Stop met zoeken.
                        except Exception:
                            continue
                            
                    if not best_audio_url:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}' in the database."
                        })
                        return {"status": "ok"}
                        
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Found: {title}! Downloading full track..."
                    })
                    
                    # --- DOWNLOAD & STUUR NAAR TELEGRAM ---
                    audio_res = await client.get(best_audio_url, follow_redirects=True, timeout=120.0)
                    os.makedirs("downloads", exist_ok=True)
                    file_path = f"downloads/{chat_id}_full.m4a"
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_res.content)
                        
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
                        
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An error occurred while downloading."
                    })
                    
    return {"status": "ok"}