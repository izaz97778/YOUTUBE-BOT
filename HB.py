import os
import re
import math
import time
import asyncio
from functools import partial
from pytube import YouTube, Playlist
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --------------------------
# Initialize Bot
# --------------------------
HB = Client(
    "YOUTUBE Bot",
    bot_token=os.environ["BOT_TOKEN"],
    api_id=int(os.environ["API_ID"]),
    api_hash=os.environ["API_HASH"]
)

# --------------------------
# Texts & Buttons
# --------------------------
START_TEXT = """**Hi {},\nI am an Advanced YouTube Downloader Bot.
I can download videos, audio, thumbnails, and playlists.
Made by @TELSABOTS**"""

HELP_TEXT = """**Send any YouTube URL and select quality.
Supports playlists too.**"""

ABOUT_TEXT = """**Bot: YouTube Downloader
Developer: @ALLUADDICT
Language: Python3
Framework: Pyrogram**"""

START_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📢CHANNEL📢", url="https://t.me/TELSABOTS"),
     InlineKeyboardButton("🧑🏼‍💻DEV🧑🏼‍💻", url="https://t.me/alluaddict")],
    [InlineKeyboardButton("🆘HELP🆘", callback_data="help"),
     InlineKeyboardButton("🤗ABOUT🤗", callback_data="about"),
     InlineKeyboardButton("🔐CLOSE🔐", callback_data="close")]
])

RESULT_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📢CHANNEL📢", url="https://t.me/TELSABOTS"),
     InlineKeyboardButton("🧑🏼‍💻DEV🧑🏼‍💻", url="https://t.me/alluaddict")],
    [InlineKeyboardButton("🔐CLOSE🔐", callback_data="close")]
])

# --------------------------
# Helper Functions
# --------------------------
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: 'B', 1: 'KiB', 2: 'MiB', 3: 'GiB', 4: 'TiB'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size,2)} {Dic_powerN[n]}"

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((f"{days}d, ") if days else "") + \
          ((f"{hours}h, ") if hours else "") + \
          ((f"{minutes}m, ") if minutes else "") + \
          ((f"{seconds}s, ") if seconds else "")
    return tmp[:-2]

async def download_stream(stream, filename):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(stream.download, filename=filename))

# Per-user download storage
user_data = {}

# --------------------------
# Command Handlers
# --------------------------
@HB.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        START_TEXT.format(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=START_BUTTONS
    )

@HB.on_message(filters.command("help"))
async def help_msg(_, message):
    await message.reply_text(
        HELP_TEXT,
        disable_web_page_preview=True,
        reply_markup=START_BUTTONS
    )

@HB.on_message(filters.command("about"))
async def about_msg(_, message):
    await message.reply_text(
        ABOUT_TEXT,
        disable_web_page_preview=True,
        reply_markup=START_BUTTONS
    )

# --------------------------
# Video Handler
# --------------------------
VIDEO_REGEX = r'(.*)youtube.com/(.*)[&|?]v=(?P<video>[^&]*)(.*)'

@HB.on_message(filters.regex(VIDEO_REGEX))
async def download_video(_, message):
    url = message.text
    chat_id = message.chat.id

    try:
        yt = YouTube(url)
    except Exception:
        return await message.reply_text("❌ Failed to fetch YouTube video.")

    user_data[chat_id] = {"yt": yt}

    # Get streams
    ythd = yt.streams.get_highest_resolution()
    ytlow = yt.streams.get_by_resolution("360p")
    ytaudio = yt.streams.filter(only_audio=True).first()

    user_data[chat_id].update({"ythd": ythd, "ytlow": ytlow, "ytaudio": ytaudio})

    # Sizes
    hd_size = humanbytes(ythd.filesize)
    low_size = humanbytes(ytlow.filesize)
    audio_size = humanbytes(ytaudio.filesize)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎬720P ⭕️ {hd_size}", callback_data="high"),
         InlineKeyboardButton(f"🎬360P ⭕️ {low_size}", callback_data="360p")],
        [InlineKeyboardButton(f"🎧AUDIO ⭕️ {audio_size}", callback_data="audio")],
        [InlineKeyboardButton("🖼THUMBNAIL🖼", callback_data="thumbnail")]
    ])

    await message.reply_photo(
        photo=yt.thumbnail_url,
        caption=f"🎬 {yt.title}\n📤 Uploaded by: {yt.author}\n📢 Channel: https://www.youtube.com/channel/{yt.channel_id}",
        reply_markup=buttons
    )

# --------------------------
# Playlist Handler
# --------------------------
@HB.on_message(filters.text & filters.private)
async def download_playlist(_, message):
    url = message.text
    chat_id = message.chat.id

    try:
        pl = Playlist(url)
    except Exception:
        return await message.reply_text("❌ Invalid playlist URL.")

    for video in pl.videos:
        try:
            phd = video.streams.get_highest_resolution()
            filename = sanitize_filename(video.title)
            await download_stream(phd, filename=f"{filename}.mp4")
            await HB.send_video(
                chat_id=chat_id,
                video=f"{filename}.mp4",
                caption=f"⭕️ Playlist: {pl.title}\n✅ JOIN @TELSABOTS"
            )
        except Exception:
            await HB.send_message(chat_id, f"⚠ Failed to download {video.title}")
        await asyncio.sleep(1)  # small delay to avoid flooding

# --------------------------
# Callback Query
# --------------------------
@HB.on_callback_query()
async def cb_query(bot, update):
    chat_id = update.message.chat.id
    data = update.data

    if chat_id not in user_data:
        return await update.message.delete()

    yt = user_data[chat_id]["yt"]

    try:
        if data == "high":
            stream = user_data[chat_id]["ythd"]
            filename = sanitize_filename(yt.title) + ".mp4"
            await download_stream(stream, filename)
            await HB.send_video(chat_id=chat_id, video=filename, caption="✅ JOIN @TELSABOTS")
        elif data == "360p":
            stream = user_data[chat_id]["ytlow"]
            filename = sanitize_filename(yt.title) + ".mp4"
            await download_stream(stream, filename)
            await HB.send_video(chat_id=chat_id, video=filename, caption="✅ JOIN @TELSABOTS")
        elif data == "audio":
            stream = user_data[chat_id]["ytaudio"]
            filename = sanitize_filename(yt.title) + ".mp3"
            await download_stream(stream, filename)
            await HB.send_audio(chat_id=chat_id, audio=filename, caption="✅ JOIN @TELSABOTS", duration=yt.length)
        elif data == "thumbnail":
            await HB.send_photo(chat_id=chat_id, photo=yt.thumbnail_url, caption="✅ JOIN @TELSABOTS")
        elif data == "home":
            await update.message.edit_text(START_TEXT.format(update.from_user.mention), reply_markup=START_BUTTONS)
        elif data == "help":
            await update.message.edit_text(HELP_TEXT, reply_markup=START_BUTTONS)
        elif data == "about":
            await update.message.edit_text(ABOUT_TEXT, reply_markup=START_BUTTONS)
        else:
            await update.message.delete()
    except Exception:
        await update.message.reply_text("❌ Error sending file, maybe file is too large.")

# --------------------------
# Run Bot
# --------------------------
print("HB YouTube Downloader Bot Started")
HB.run()
