import os
import httpx
import yt_dlp
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
                    "text": f"⬇️ Searching and downloading full track from SoundCloud: '{query}'..."
                })
                
                try:
                    # Gebruik SoundCloud via yt-dlp om YouTube-blokkades compleet te omzeilen
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': 'downloads/%(id)s.%(ext)s',
                        'noplaylist': True,
                        'max_filesize': 50000000, # Maximaal 50MB per bestand
                    }
                    
                    os.makedirs("downloads", exist_ok=True)
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # scsearch: zorgt dat hij SoundCloud doorzoekt in plaats van YouTube
                        info = ydl.extract_info(f"scsearch:{query}", download=True)
                        
                        if 'entries' in info and len(info['entries']) > 0:
                            video_info = info['entries'][0]
                        else:
                            video_info = info
                            
                        file_path = ydl.prepare_filename(video_info)
                        title = video_info.get('title', query)
                        performer = video_info.get('uploader', 'Unknown Artist')
                    
                    # Stuur het bestand als echte muziekspeler naar Telegram
                    with open(file_path, "rb") as audio_file:
                        files = {"audio": audio_file}
                        data_payload = {
                            "chat_id": chat_id,
                            "title": title,
                            "performer": performer,
                            "caption": f"🎵 {title} - {performer} (Full Track)"
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
                    import traceback
                    fout_melding = traceback.format_exc()
                    print(f"❌ ERROR: {fout_melding}")
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ An error occurred while fetching the track: {str(e)[:100]}"
                    })
                    
    return {"status": "ok"}