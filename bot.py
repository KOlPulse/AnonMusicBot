import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Je automatische Render URL
WEBHOOK_URL = "https://anonmusicbot-b73b.onrender.com/webhook"

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return {"status": "Anon Music Bot Webhook is online en gezond!"}

# 1. Automatisch de webhook instellen bij opstarten van Render
@app.on_event("startup")
async def startup_event():
    print("==== Instellen van Telegram Webhook... ====")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"Webhook registratie antwoord: {response.text}")
    print("==== WEBHOOK SERVER IS KLAAR VOOR ACTIE! ====")

# 2. Hier vangt Render de berichten op die Telegram naar ons stuurt
@app.post("/webhook")
async def receive_update(request: Request):
    data = await request.json()
    
    # Check of er een bericht in zit
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        user_name = message["from"].get("first_name", "Vriend")
        
        print(f"🚨 WEBHOOK ALERT: Bericht ontvangen van {user_name}: '{text}'")
        
        # Als iemand /start typt, sturen we direct antwoord via Telegram API
        if text.startswith("/start"):
            reply_text = f"🤖 Vibe on, {user_name}! De Webhook-versie van Anon Music Bot is wakker en klaar voor actie!"
            
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(send_url, json={
                    "chat_id": chat_id,
                    "text": reply_text
                })
                
    return {"status": "ok"}