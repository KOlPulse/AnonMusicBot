# server.py
import os
from aiohttp import web

async def health_check(request):
    return web.Response(text="Music Bot is alive and well", status=200)

app = web.Application()
app.router.add_get('/', health_check)

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))
    print(f"==== STARTING SIMPLE SERVER ON PORT {PORT} ====")
    web.run_app(app, host='0.0.0.0', port=PORT)