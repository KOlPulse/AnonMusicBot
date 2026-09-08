import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pytgcalls import PyTgCalls

# 1. Haal de geheime sleutels uit je .env kluis
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2. Maak de connectie met Telegram
app = Client(
    "AnonMusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 3. Bereid de audio-speler voor (voor de Voice Chats)
call_py = PyTgCalls(app)

# 4. Een simpel test-commando om te zien of hij leeft
@app.on_message(filters.command("start"))
async def start_commando(client, message):
    await message.reply_text("🤖 Vibe on! De Anon Music Bot is wakker en klaar voor actie!")

# 5. Start de motor!
if __name__ == "__main__":
    print("Bot is aan het opstarten...")
    call_py.run()