import logging
import sys
import asyncio
import schedule
import os
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from modules.moderation import check_message, contains_restricted_chars
from modules.ai import ai_response
from modules.database import (
    add_admin, remove_admin, get_admins, 
    add_banned_user, remove_banned_user, get_banned_users,
    add_banned_word, remove_banned_word
)
from modules.log_cleaner import clean_logs

# Pastikan folder logs/ ada
if not os.path.exists("logs"):
    os.makedirs("logs")

# Konfigurasi logging yang benar untuk Python 3.8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Inisialisasi bot Telethon dengan connection_pool_size untuk menghindari database lock
bot = TelegramClient("hirokesbot", API_ID, API_HASH, connection_pool_size=100).start(bot_token=BOT_TOKEN)

# Memuat daftar admin dan pengguna yang diblokir dari database
admin_list = get_admins()
banned_users = get_banned_users()

# Variabel kontrol bot
bot_aktif = False
bot_expiry = None

# Menjadwalkan pembersihan log setiap 7 hari
schedule.every(7).days.do(clean_logs)

async def run_schedule():
    """Menjalankan schedule secara asinkron"""
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    """Menampilkan pesan sambutan bot."""
    await event.respond(
        "🛡️ **HirokesBot Aktif!** 🛡️\n"
        "Saya bisa membantu mengamankan grup dari spammer dan kata terlarang.\n\n"
        "🔹 Tambahkan saya ke grup dan jadikan admin hubungi @hiro_v1.\n"
        "🔹 Gunakan /help untuk daftar perintah."
    )

@bot.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    """Menampilkan daftar perintah bot."""
    help_text = """**📜 Daftar Perintah HirokesBot 📜**
    
    **🔹 Admin Commands:**
    - /kontrol → Menampilkan tombol ON & OFF
    - /inbl (reply user) → Blokir pengguna (pesannya selalu dihapus)
    - /bl (reply text or typing text) → Tambah kata terlarang
    - /unbl (reply text or typing text) → Hapus kata terlarang

    **🔹 Owner Commands (@hiro_v1):**
    - /aktifbt → Aktifkan bot selama 1 bulan
    - /unak → Matikan bot
    - /ceklog → Kirim file log ke owner
    - /kontrol → Menampilkan tombol ON & OFF
    - /adm (reply user) → Tambah admin yang bisa mengontrol bot 
    - /unbl (reply user) → Hapus pengguna dari daftar blokir 
    - /unadm (reply user) → Hapus admin dari daftar kontrol

    **🔹 All Users:**
    - /ask → Mengajukan pertanyaan ke AI HirokesBot
    """
    await event.respond(help_text)

@bot.on(events.NewMessage(pattern="/adm"))
async def tambah_admin(event):
    """Menambahkan admin yang dapat mengontrol bot."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id
     
