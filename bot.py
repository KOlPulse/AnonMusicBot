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
                    "text": f"🔍 Searching for full track: '{query}'..."
                })
                
                try:
                    # Nieuwe, werkende Muziek API server (saavn.me)
                    search_url = f"https://saavn.me/search/songs?query={query}"
                    res = await client.get(search_url)
                    api_data = res.json()
                    
                    # saavn.me gebruikt 'status': 'SUCCESS'
                    if api_data.get("status") == "SUCCESS" and api_data.get("data", {}).get("results"):
                        song = api_data["data"]["results"][0]
                        title = song.get("name", query).replace("&quot;", '"').replace("&amp;", "&")
                        artists = song.get("primaryArtists", "Unknown Artist")
                        download_urls = song.get("downloadUrl", [])
                        
                        if download_urls:
                            # Pak de hoogste audiokwaliteit
                            best_audio_url = download_urls[-1]["url"]
                            
                            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"✅ Found it! Downloading full track: {title}... (Give me a few seconds)"
                            })
                            
                            audio_res = await client.get(best_audio_url, follow_redirects=True)
                            os.makedirs("downloads", exist_ok=True)
                            file_path = f"downloads/{chat_id}_full.m4a"
                            
                            with open(file_path, "wb") as f:
                                f.write(audio_res.content)
                                
                            with open(file_path, "rb") as audio_file:
                                files = {"audio": audio_file}
                                data_payload = {
                                    "chat_id": chat_id,
                                    "title": title,
                                    "performer": artists,
                                    "caption": f"🎵 {title} - {artists} (Full Track)"
                                }
                                await client.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio",
                                    data=data_payload,
                                    files=files,
                                    timeout=120.0
                                )
                                
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        else:
                            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "❌ Found the song, but no download links are available."
                            })
                    else:
                        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"❌ Could not find '{query}'."
                        })
                        
                except Exception as e:
                    print(f"❌ ERROR: {e}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ The music server is temporarily unreachable. Try again in a minute!"
                    })
                    
    return {"status": "ok"}