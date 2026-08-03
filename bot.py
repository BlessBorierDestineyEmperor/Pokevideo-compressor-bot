import os
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ===== PLACE YOUR CREDENTIALS HERE =====
API_ID = 34949424  # Replace with your API ID from my.telegram.org
API_HASH = "edd20208c3046743b9fc0cbbd39a1b3d"  # Replace with your API Hash
BOT_TOKEN = "7077933360:AAGz65EM0ZWPZvno_nJdQDYdBzXrUupm_VU"  # Replace with your Bot Token from @BotFather

app = Client("CompressorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_videos = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 **Hello! Send me a video, and I will compress it into multiple qualities.**")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    if message.document and not message.document.mime_type.startswith("video/"):
        return

    msg = await message.reply_text("📥 **Processing video information...**")
    
    file_id = message.video.file_id if message.video else message.document.file_id
    user_videos[message.chat.id] = file_id

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 1080p (High)", callback_data="compress_1080")],
        [InlineKeyboardButton("🎥 720p (Medium)", callback_data="compress_720")],
        [InlineKeyboardButton("🎥 480p (Low)", callback_data="compress_480")],
        [InlineKeyboardButton("🎥 360p (Very Low)", callback_data="compress_360")]
    ])

    await msg.edit_text("⚙️ **Select the target quality for compression:**", reply_markup=buttons)

@app.on_callback_query(filters.regex(r"^compress_"))
async def compress_callback(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    quality = callback_query.data.split("_")[1]

    if chat_id not in user_videos:
        await callback_query.answer("❌ Video not found! Please send the video again.", show_alert=True)
        return

    await callback_query.message.edit_text(f"⏳ **Starting compression to {quality}p... Please wait.**")

    input_path = f"downloads/{chat_id}_input.mp4"
    output_path = f"downloads/{chat_id}_{quality}p.mp4"

    try:
        await callback_query.message.edit_text("⬇️ **Downloading video to server...**")
        file_id = user_videos[chat_id]
        await client.download_media(message=file_id, file_name=input_path)

        await callback_query.message.edit_text(f"⚙️ **Compressing to {quality}p via FFmpeg...**")
        
        scale_dict = {
            "1080": "scale=-2:1080",
            "720": "scale=-2:720",
            "480": "scale=-2:480",
            "360": "scale=-2:360"
        }
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", scale_dict[quality],
            "-c:v", "libx264", "-crf", "28", "-preset", "faster",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        process = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
        await process.communicate()

        await callback_query.message.edit_text("📤 **Uploading compressed video to Telegram...**")
        await client.send_video(
            chat_id=chat_id,
            video=output_path,
            caption=f"✅ **Successfully compressed to {quality}p!**"
        )
        await callback_query.message.delete()

    except Exception as e:
        await callback_query.message.edit_text(f"❌ **Error occurred:** `{str(e)}`")

    finally:
        for path in [input_path, output_path]:
            if os.path.exists(path):
                os.remove(path)
        user_videos.pop(chat_id, None)

if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    print("🤖 Bot Started...")
    app.run()
