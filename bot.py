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
    return {"status": "Anon Music Bot Webhook is online and ready for music!"}

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
                    "text": f"🔍 Please wait {user_name}, searching for '{query}' on YouTube..."
                })
                
                try:
                    # yt-dlp opties geoptimaliseerd zonder cookies-bestand
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': 'downloads/%(id)s.%(ext)s',
                        'noplaylist': True,
                        'max_filesize': 50000000,
                        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
                    }
                    
                    os.makedirs("downloads", exist_ok=True)
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"ytsearch:{query}", download=True)
                        if 'entries' in info:
                            video_info = info['entries'][0]
                        else:
                            video_info = info
                            
                        file_path = ydl.prepare_filename(video_info)
                        title = video_info.get('title', 'Music Track')
                        performer = video_info.get('uploader', 'YouTube')
                    
                    with open(file_path, "rb") as audio_file:
                        files = {"audio": audio_file}
                        data_payload = {
                            "chat_id": chat_id,
                            "title": title,
                            "performer": performer,
                            "caption": f"🎵 Here is your track: {title}"
                        }
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio",
                            data=data_payload,
                            files=files,
                            timeout=60.0
                        )
                        
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    import traceback
                    fout_melding = traceback.format_exc()
                    print(f"❌ DETAILED ERROR: {fout_melding}")
                    
                    await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"❌ Error: {str(e)[:100]}"
                    })
                    
    return {"status": "ok"}