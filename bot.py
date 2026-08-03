from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Start HTTP server in a separate thread
threading.Thread(target=run_web_server, daemon=True).start()

# ===== PLACE YOUR CREDENTIALS HERE =====
API_ID = 34949424
API_HASH = "edd20208c3046743b9fc0cbbd39a1b3d"
BOT_TOKEN = "7077933360:AAGz65EM0ZwPZvno_nJdQDYdBzXrUupm_VU"

app = Client("CompressorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_videos = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **Hello! Send me a video, and I will compress it.**")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    if message.document and not message.document.mime_type.startswith("video/"):
        return

    msg = await message.reply_text("📥 **Processing video information...**")
    file_id = message.video.file_id if message.video else message.document.file_id
    user_videos[message.chat.id] = file_id

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 1080p (High)", callback_data="compress_1080")],
        [InlineKeyboardButton("📹 720p (Medium)", callback_data="compress_720")],
        [InlineKeyboardButton("📹 480p (Low)", callback_data="compress_480")]
    ])
    
    await msg.edit_text("🎬 **Choose resolution to compress:**", reply_markup=buttons)

if __name__ == "__main__":
    app.run()
