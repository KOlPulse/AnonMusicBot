import os
import httpx
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
                    "text": f"🔍 Proxy searching the network for: '{query}'..."
                })
                
                try:
                    # Het netwerk van onafhankelijke Proxy servers
                    piped_instances = [
                        "https://pipedapi.kavin.rocks",
                        "https://pipedapi.drgns.space",
                        "https://pipedapi.smnz.de",
                        "https://pipedapi.adminforge.de"
                    ]
                    
                    best_audio_url = None
                    title = None
                    author = None
                    
                    for instance in piped_instances:
                        try:
                            # 1. Zoek het nummer
                            search_url = f"{instance}/search?q={query}&filter=music_songs"
                            res = await client.get(search_url, timeout=10.0)
                            
                            # Als de server een foutpagina teruggeeft in plaats van code, negeer deze dan
                            if res.status_code != 200:
                                continue
                                
                            try:
                                api_data = res.json()
                            except Exception:
                                continue # Sla over als de JSON kapot is
                                
                            items = api_data.get("items", [])
                            if not items:
                                continue
                                
                            video_url = items[0].get("url", "")
                            video_id = video_url.split("?v=")[-1]
                            title = items[0].get("title", query).replace("&quot;", '"')
                            author = items[0].get("uploaderName", "Unknown Artist")
                            
                            # 2. Haal de directe, geproxiede audio stream op
                            stream_res = await client.get(f"{instance}/streams/{video_id}", timeout=10.0)
                            if stream_res.status_code != 200:
                                continue
                                
                            try:
                                stream_data = stream_res.json()
                            except Exception:
                                continue
                                
                            audio_streams = stream_data.get("audioStreams", [])
                            for stream in audio_streams:
                                # We willen de m4a/mp4a stream voor perfecte Telegram integratie (itag 140)
                                if "mp4" in stream.get("mimeType", "") or "m4a" in stream.get("mimeType", ""):
                                    best_audio_url = stream.get("url")
                                    break
                                    
                            if best_audio_url:
                                break # We hebben een werkende link! Breek uit de loop.
                                
                        except Exception as inner_e:
                            print(f"Skipping proxy {instance} due to error: {inner_e}")
                            continue # Server onbereikbaar? Probeer direct de volgende in de lijst!
                            
                    if not best_audio_url:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ All proxy servers are currently busy or the track is unavailable."
                        })
                        return {"status": "ok"}
                        
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"✅ Found an unlocked proxy stream! Uploading {title}..."
                    })
                    
                    # 3. Download audio lokaal via de proxy
                    audio_res = await client.get(best_audio_url, follow_redirects=True, timeout=120.0)
                    
                    # Zekerheidscheck: Is het bestand groter dan 100KB? (Voorkomt 00:00 ghost files)
                    if len(audio_res.content) < 100000:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ The audio stream was empty. Please try another track."
                        })
                        return {"status": "ok"}
                        
                    os.makedirs("downloads", exist_ok=True)
                    file_path = f"downloads/{chat_id}_full.m4a"
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_res.content)
                        
                    # 4. Stuur het volledige bestand als speler naar Telegram
                    with open(file_path, "rb") as audio_file:
                        files = {"audio": audio_file}
                        data_payload = {
                            "chat_id": chat_id,
                            "title": title,
                            "performer": author,
                            "caption": f"🎵 {title} - {author} (Full Track)"
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
                    error_msg = str(e)
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ TECHNISCHE FOUT: {error_msg}"
                    })
                    
    return {"status": "ok"}