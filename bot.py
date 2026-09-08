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
        
        async with httpx.AsyncClient() as client:
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
                    "text": f"🔍 Searching for '{query}'..."
                })
                
                try:
                    search_url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
                    res = await client.get(search_url)
                    result_data = res.json()
                    
                    if result_data["resultCount"] > 0:
                        song = result_data["results"][0]
                        track_name = song.get("trackName", query)
                        artist_name = song.get("artistName", "Unknown Artist")
                        preview_url = song.get("previewUrl")
                        
                        if preview_url:
                            # Download het audiobestand eerst lokaal als .m4a/.mp3
                            audio_res = await client.get(preview_url)
                            os.makedirs("downloads", exist_ok=True)
                            file_path = f"downloads/{chat_id}.m4a"
                            
                            with open(file_path, "wb") as f:
                                f.write(audio_res.content)
                                
                            # Stuur het bestand nu als echte audio naar Telegram
                            with open(file_path, "rb") as audio_file:
                                files = {"audio": audio_file}
                                data_payload = {
                                    "chat_id": chat_id,
                                    "title": track_name,
                                    "performer": artist_name,
                                    "caption": f"🎵 {track_name} - {artist_name}"
                                }
                                await client.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio",
                                    data=data_payload,
                                    files=files,
                                    timeout=60.0
                                )
                                
                            # Ruim het bestand lokaal op
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        else:
                            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "❌ No audio stream found for this track."
                            })
                    else:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}'. Try another search!"
                        })
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "❌ An error occurred while fetching the track."
                    })