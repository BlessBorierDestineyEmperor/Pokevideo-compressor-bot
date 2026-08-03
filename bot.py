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
BOT_TOKEN = "7077933360:AAF2TFCnz26CHus-LZ7--hqyQ5lrL5LMg6s"

app = Client("CompressorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_videos = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **হ্যালো! আমাকে যেকোনো ভিডিও পাঠান, আমি সেটি কম্প্রেস করে দেবো।**")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    if message.document and not message.document.mime_type.startswith("video/"):
        return

    msg = await message.reply_text("📥 **ভিডিও ইনফরমেশন প্রসেস হচ্ছে...**")
    file_id = message.video.file_id if message.video else message.document.file_id
    user_videos[message.chat.id] = file_id

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 1080p (High)", callback_data="compress_1080")],
        [InlineKeyboardButton("📹 720p (Medium)", callback_data="compress_720")],
        [InlineKeyboardButton("📹 480p (Low)", callback_data="compress_480")]
    ])
    
    await msg.edit_text("🎬 **কোন রেজুলেশনে কম্প্রেস করতে চান সিলেক্ট করুন:**", reply_markup=buttons)

@app.on_callback_query(filters.regex("compress_"))
async def callback_compression(client, callback_query):
    query_data = callback_query.data
    chat_id = callback_query.message.chat.id
    
    if chat_id not in user_videos:
        await callback_query.answer("⚠️ অনুগ্রহ করে ভিডিওটি আবার পাঠান!", show_alert=True)
        return

    resolution = query_data.split("_")[1]
    await callback_query.answer(f"🚀 {resolution} কম্প্রেশন শুরু হচ্ছে...")
    status_msg = await callback_query.message.edit_text(f"📥 **ভিডিও ডাউনলোড হচ্ছে... দয়া করে অপেক্ষা করুন।**")

    file_id = user_videos[chat_id]
    
    try:
        # 1. Download video from Telegram
        input_file = await client.download_media(file_id, file_name=f"downloads/{chat_id}.mp4")
        
        await status_msg.edit_text(f"⚙️ **ভিডিও কম্প্রেস হচ্ছে ({resolution})...**")
        
        output_file = f"downloads/compressed_{chat_id}.mp4"
        
        # Set resolution scale based on user choice
        scale_filter = "scale=-2:480"
        if resolution == "1080":
            scale_filter = "scale=-2:1080"
        elif resolution == "720":
            scale_filter = "scale=-2:720"

        # 2. Compress using FFmpeg
        cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", scale_filter,
            "-c:v", "libx264", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            output_file, "-y"
        ]
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if process.returncode != 0:
            await status_msg.edit_text("❌ **কম্প্রেশন ফেইল করেছে!**")
            return

        await status_msg.edit_text(f"📤 **কম্প্রেসড ভিডিও আপলোড হচ্ছে...**")
        
        # 3. Send compressed video back to user
        await client.send_video(
            chat_id=chat_id,
            video=output_file,
            caption=f"✅ **কম্প্রেশন সফল ({resolution}p)!**"
        )
        
        await status_msg.delete()

        # Clean up files
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

    except Exception as e:
        await status_msg.edit_text(f"❌ **ত্রুটি দেখা দিয়েছে:** `{str(e)}`")

if __name__ == "__main__":
    app.run()
