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
                    "text": f"🔍 Searching securely for: '{query}'..."
                })
                
                try:
                    # STAP 1: Zoeken via Invidious (Dit werkt perfect zoals we zagen)
                    invidious_instances = ["https://yewtu.be", "https://vid.puffyan.us", "https://invidious.flokinet.to"]
                    video_id, title, author = None, None, None
                    
                    for instance in invidious_instances:
                        try:
                            search_url = f"{instance}/api/v1/search?q={query}"
                            res = await client.get(search_url, timeout=10.0)
                            if res.status_code == 200:
                                api_data = res.json()
                                video = next((v for v in api_data if v.get("type") == "video"), None)
                                if video:
                                    video_id = video["videoId"]
                                    title = video["title"]
                                    author = video["author"]
                                    break
                        except Exception:
                            continue
                            
                    if not video_id:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}'."
                        })
                        return {"status": "ok"}
                        
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Found: {title}\n⬇️ Downloading high quality audio via Cobalt API..."
                    })
                    
                    # STAP 2: Ophalen via de Cobalt API (Bypass voor de lege 00:00 bestanden)
                    cobalt_url = "https://api.cobalt.tools/api/json"
                    cobalt_headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    cobalt_payload = {
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "aFormat": "mp3",
                        "isAudioOnly": True
                    }
                    
                    cobalt_res = await client.post(cobalt_url, json=cobalt_payload, headers=cobalt_headers, timeout=30.0)
                    cobalt_data = cobalt_res.json()
                    
                    audio_url = cobalt_data.get("url")
                    
                    if not audio_url:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ The download server is currently busy. Try again!"
                        })
                        return {"status": "ok"}
                        
                    # STAP 3: Audio lokaal opslaan
                    audio_res = await client.get(audio_url, follow_redirects=True, timeout=120.0)
                    
                    # VEILIGHEIDSCHECK: Is het bestand groter dan 100KB? Zo niet, dan is het een nepbestand (00:00)
                    if len(audio_res.content) < 100000:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ YouTube blocked the stream (File is empty). Please try another song."
                        })
                        return {"status": "ok"}
                        
                    os.makedirs("downloads", exist_ok=True)
                    file_path = f"downloads/{chat_id}_full.mp3"
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_res.content)
                        
                    # STAP 4: Echte muziekspeler naar Telegram sturen
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
                        
                    # Opruimen
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An unexpected error occurred while downloading."
                    })
                    
    return {"status": "ok"}