from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
import asyncio
import time
import re
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

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

async def progress_bar(current, total, message, text):
    now = time.time()
    if hasattr(message, "last_update") and now - message.last_update < 2:
        return
    message.last_update = now
    
    percentage = current * 100 / total if total > 0 else 0
    completed = int(percentage / 10)
    bar = "█" * completed + "░" * (10 - completed)
    
    try:
        await message.edit_text(
            f"<b>{text}</b>\n\n"
            f"[{bar}] {percentage:.1f}%\n"
            f"📊 <b>Size:</b> {human_readable_size(current)} / {human_readable_size(total)}"
        )
    except Exception:
        pass

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **Hello! Send me any video, and I will compress it for you.**")

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
    status_msg = await callback_query.message.edit_text(f"📥 **Starting download...**")

    file_id = user_videos[chat_id]
    
    try:
        os.makedirs("downloads", exist_ok=True)
        input_file = f"downloads/{chat_id}.mp4"
        
        # 1. Download with Progress
        await client.download_media(
            file_id,
            file_name=input_file,
            progress=progress_bar,
            progress_args=(status_msg, "📥 Downloading Video...")
        )
        
        await status_msg.edit_text(f"⚙️ **Getting video duration...**")
        
        # Get total duration of the video using ffprobe
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_file]
        probe_process = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            total_duration = float(probe_process.stdout.strip())
        except Exception:
            total_duration = 0

        output_file = f"downloads/compressed_{chat_id}.mp4"
        
        scale_filter = "scale=-2:480"
        if resolution == "1080":
            scale_filter = "scale=-2:1080"
        elif resolution == "720":
            scale_filter = "scale=-2:720"

        # 2. Compress using FFmpeg with Live Percentage Parsing
        cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", scale_filter,
            "-c:v", "libx264", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            output_file, "-y"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        
        last_time = 0
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Extract 'time=00:00:00.00' from ffmpeg output
                time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", output)
                if time_match and total_duration > 0:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = int(time_match.group(3))
                    current_seconds = hours * 3600 + minutes * 60 + seconds
                    
                    percentage = min(current_seconds * 100 / total_duration, 100.0)
                    
                    # Update message every 2 seconds to avoid flood-wait errors
                    now = time.time()
                    if now - last_time >= 2:
                        last_time = now
                        completed = int(percentage / 10)
                        bar = "█" * completed + "░" * (10 - completed)
                        try:
                            await status_msg.edit_text(
                                f"<b>⚙️ Compressing Video ({resolution}p)...</b>\n\n"
                                f"[{bar}] {percentage:.1f}%\n"
                                f"⏳ <b>Progress:</b> {current_seconds}s / {int(total_duration)}s"
                            )
                        except Exception:
                            pass

        if process.returncode != 0:
            await status_msg.edit_text("❌ **Compression failed!**")
            return

        await status_msg.edit_text(f"📤 **Starting upload...**")
        
        # 3. Upload with Progress
        await client.send_video(
            chat_id=chat_id,
            video=output_file,
            caption=f"✅ **Compression successful ({resolution}p)!**",
            progress=progress_bar,
            progress_args=(status_msg, "📤 Uploading Compressed Video...")
        )
        
        await status_msg.delete()

        # Clean up files
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

    except Exception as e:
        await status_msg.edit_text(f"❌ **An error occurred:** `{str(e)}`")

if __name__ == "__main__":
    app.run()
