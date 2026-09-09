import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import yt_dlp

# 1. Dummy Web Server (Dit houdt Render blij op de achtergrond, gescheiden van de bot!)
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"De Muziek Bot draait succesvol!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    server.serve_forever()

# Start de server in een aparte "thread" zodat hij de bot niet blokkeert
threading.Thread(target=run_web_server, daemon=True).start()

# 2. Telegram Bot Instellingen
API_ID = 38561709
API_HASH = "45cb3c0d9a016faa268a269245e6fe4e"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client(
    "VibeMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(app)

# 3. Helper functie voor YouTube download
def get_audio_url(query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info.get('title', 'Onbekend nummer')

# 4. Bot Commando's
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("👋 Welcome to **AnonMusicBot**! Gebruik `/play` in een GROEP om muziek te luisteren.")

@app.on_message(filters.command("play"))
async def play_handler(client, message):
    # BLOKKEER PRIVÉBERICHTEN
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text("❌ Je kunt alleen muziek afspelen in een **Groep** met een actieve Voice Chat, niet hier in een privébericht!")
        return

    if len(message.command) < 2:
        await message.reply_text("⚠️ Gebruik: `/play [naam van het nummer]`")
        return

    query = " ".join(message.command[1:])
    chat_id = message.chat.id
    
    status_msg = await message.reply_text(f"🔍 Zoeken naar **{query}**...")

    try:
        audio_url, title = await asyncio.to_thread(get_audio_url, query)
        await status_msg.edit_text(f"🎵 Verbinden met de Voice Chat voor: **{title}**...")

        await call_py.play(
            chat_id,
            MediaStream(audio_url)
        )
        
        await status_msg.edit_text(f"🎶 Nu live te horen in de Voice Chat: **{title}**!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Er is een fout opgetreden: {str(e)}")

# 5. Start de applicatie natively
async def main():
    await app.start()
    await call_py.start()
    print("Telegram Bot en Voice Chat DJ draaien nu vlekkeloos!")
    await asyncio.gather(
        app.idle(),
        call_py.idle()
    )

if __name__ == "__main__":
    asyncio.run(main())