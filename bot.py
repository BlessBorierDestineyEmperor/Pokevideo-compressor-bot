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
BOT_TOKEN = "7077933360:AAF2TFCnz26CHus-LZ7--hqyQ51rL5LMg6s"

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

@app.on_callback_query(filters.regex("compress_"))
async def callback_compression(client, callback_query):
    query_data = callback_query.data
    chat_id = callback_query.message.chat.id
    
    if chat_id not in user_videos:
        await callback_query.answer("⚠️ Please send the video again!", show_alert=True)
        return

    resolution = query_data.split("_")[1]
    await callback_query.answer(f"🚀 Starting {resolution} compression...")
    await callback_query.message.edit_text(f"⏳ **Downloading and compressing to {resolution}... Please wait.**")

    # Future compression process execution can be added here
    await asyncio.sleep(3)
    await callback_query.message.edit_text(f"✅ **Compression to {resolution} completed successfully!** (Demo mode)")

if __name__ == "__main__":
    app.run()
