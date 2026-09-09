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
        
        # We zetten een langere timeout (120 seconden) omdat hele nummers downloaden even duurt
        async with httpx.AsyncClient(timeout=120.0) as client:
            if text.startswith("/start"):
                reply_text = f"🤖 Vibe on, {user_name}! Type **/play [song name]** to search and listen to music!"
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
                    "text": f"🔍 Searching for full track: '{query}'..."
                })
                
                try:
                    # 1. Zoeken via de Piped API (omzeilt YouTube IP blokkades)
                    search_url = f"https://pipedapi.kavin.rocks/search?q={query}&filter=all"
                    res = await client.get(search_url)
                    search_data = res.json()
                    
                    items = search_data.get("items", [])
                    if not items:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}'."
                        })
                        return {"status": "ok"}
                        
                    # Pak de eerste echte video uit de resultaten
                    video = next((item for item in items if item["type"] == "stream"), None)
                    if not video:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "❌ No valid video found."
                        })
                        return {"status": "ok"}
                        
                    # Extraheer de gegevens
                    video_id = video["url"].split("?v=")[-1]
                    title = video.get("title", "Music Track")
                    uploader = video.get("uploaderName", "Unknown Artist")
                    
                    # 2. Haal de directe audio streams op
                    streams_url = f"https://pipedapi.kavin.rocks/streams/{video_id}"
                    streams_res = await client.get(streams_url)
                    streams_data = streams_res.json()
                    
                    audio_streams = streams_data.get("audioStreams", [])
                    if not audio_streams:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "❌ No audio streams found for this video."
                        })
                        return {"status": "ok"}
                        
                    # Kies de stream met de juiste audio-indeling
                    best_audio = audio_streams[0]["url"]
                    for stream in audio_streams:
                        if stream.get("mimeType", "").startswith("audio/mp4"):
                            best_audio = stream["url"]
                            break
                            
                    # 3. Download audio lokaal (zodat Telegram de echte muziekspeler laat zien)
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"⬇️ Downloading full track: {title}... (This can take a few seconds)"
                    })
                    
                    audio_res = await client.get(best_audio, follow_redirects=True)
                    os.makedirs("downloads", exist_ok=True)
                    file_path = f"downloads/{chat_id}_full.m4a"
                    
                    with open(file_path, "wb") as f:
                        f.write(audio_res.content)
                        
                    # 4. Stuur het volledige nummer naar Telegram
                    with open(file_path, "rb") as audio_file:
                        files = {"audio": audio_file}
                        data_payload = {
                            "chat_id": chat_id,
                            "title": title,
                            "performer": uploader,
                            "caption": f"🎵 {title} - {uploader} (Full Track)"
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
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An error occurred while fetching the full track: {str(e)[:100]}"
                    })
                    
    return {"status": "ok"}