import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Webhook is online and ready!"}

@app.on_event("startup")
async def startup_event():
    print("==== Setting up Telegram Webhook... ====")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"Webhook registration response: {response.text}")
    print("==== WEBHOOK SERVER IS READY FOR ACTION! ====")

@app.post("/webhook")
async def receive_update(request: Request):
    data = await request.json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user_name = message["from"].get("first_name", "Friend")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            if text.startswith("/start"):
                reply_text = f"🤖 Vibe on, {user_name}! Type **/play [song name]** to listen to full tracks!"
                await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply_text
                })
                
            elif text.startswith("/play"):
                query = text.replace("/play", "").strip()
                if not query:
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "⚠️ Usage: /play [artist or title], for example: /play Armin van Buuren"
                    })
                    return {"status": "ok"}
                
                await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"🔍 Searching securely across the network for: '{query}'..."
                })
                
                try:
                    # Lijst met betrouwbare Invidious servers om blokkades en offline servers te omzeilen
                    invidious_instances = [
                        "https://yewtu.be",
                        "https://vid.puffyan.us",
                        "https://invidious.flokinet.to",
                        "https://inv.tux.pizza"
                    ]
                    
                    video = None
                    working_instance = None
                    
                    # Probeer de servers één voor één totdat er eentje werkt
                    for instance in invidious_instances:
                        try:
                            search_url = f"{instance}/api/v1/search?q={query}"
                            res = await client.get(search_url, timeout=10.0)
                            if res.status_code == 200:
                                api_data = res.json()
                                # Zoek de eerste echte video in de resultaten
                                video = next((v for v in api_data if v.get("type") == "video"), None)
                                if video:
                                    working_instance = instance
                                    break # We hebben een werkende server gevonden, stop met zoeken!
                        except Exception:
                            continue # Als deze server stuk is, probeer direct de volgende
                            
                    if video and working_instance:
                        video_id = video["videoId"]
                        title = video["title"]
                        author = video["author"]
                        
                        # Directe, proxy-omgeleide audio download (itag 140 = zuivere m4a audio)
                        best_audio_url = f"{working_instance}/latest_version?id={video_id}&itag=140"
                        
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"✅ Connected to {working_instance}! Downloading full track: {title}..."
                        })
                        
                        # Download audio lokaal
                        audio_res = await client.get(best_audio_url, follow_redirects=True, timeout=120.0)
                        os.makedirs("downloads", exist_ok=True)
                        file_path = f"downloads/{chat_id}_full.m4a"
                        
                        with open(file_path, "wb") as f:
                            f.write(audio_res.content)
                            
                        # Stuur als echte muziekspeler naar Telegram
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
                            
                        # Ruim de server weer netjes op
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    else:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}' or all servers are currently busy."
                        })
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An unexpected error occurred. Try again!"
                    })
                    
    return {"status": "ok"}