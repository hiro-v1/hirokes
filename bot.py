import logging
import asyncio
import schedule
import os
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from modules.moderation import check_message, contains_restricted_chars
from modules.ai import ai_response
from modules.database import add_banned_word, remove_banned_word
from modules.log_cleaner import clean_logs

# Pastikan folder logs/ ada
if not os.path.exists("logs"):
    os.makedirs("logs")

# Konfigurasi logging
logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Inisialisasi bot Telethon
bot = TelegramClient("hirokesbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Variabel kontrol bot
bot_aktif = False
admin_list = set()  # Menyimpan daftar admin yang dapat menggunakan /kontrol
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
        "🔹 Tambahkan saya ke grup dan jadikan admin.\n"
        "🔹 Gunakan /help untuk daftar perintah."
    )

@bot.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    """Menampilkan daftar perintah bot."""
    help_text = """**📜 Daftar Perintah HirokesBot 📜**
    
    **🔹 Admin Commands:**
    - /kontrol → Menampilkan tombol ON & OFF
    - /adm (reply user) → Tambah admin yang bisa mengontrol bot
    - /unadm (reply user) → Hapus admin dari daftar kontrol
    - /bl (reply text) → Tambah kata terlarang
    - /inbl (reply user) → Blokir pengguna
    - /unbl (username) → Hapus dari daftar blokir
    
    **🔹 Owner Commands (5432983527):**
    - /aktifbt → Aktifkan bot selama 1 bulan
    - /unak → Matikan bot
    - /ceklog → Kirim file log ke owner
    """
    await event.respond(help_text)

@bot.on(events.NewMessage(pattern="/adm"))
async def tambah_admin(event):
    """Menambahkan admin yang dapat mengontrol bot."""
    global admin_list
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id
        admin_list.add(user_id)
        logging.info(f"✅ Admin ditambahkan: {user_id}")
        await event.respond(f"✅ **Admin {user_id} telah ditambahkan** dan dapat menggunakan `/kontrol`.")
    else:
        await event.respond("❌ **Gunakan perintah ini dengan mereply pesan pengguna yang ingin dijadikan admin.**")

@bot.on(events.NewMessage(pattern="/unadm"))
async def hapus_admin(event):
    """Menghapus admin dari daftar kontrol bot."""
    global admin_list
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id
        if user_id in admin_list:
            admin_list.remove(user_id)
            logging.info(f"❌ Admin dihapus: {user_id}")
            await event.respond(f"❌ **Admin {user_id} telah dihapus dari daftar kontrol.**")
        else:
            await event.respond("⚠️ Pengguna ini bukan admin.")
    else:
        await event.respond("❌ **Gunakan perintah ini dengan mereply pesan pengguna yang ingin dihapus dari admin.**")

@bot.on(events.NewMessage(pattern="/aktifbt"))
async def aktifkan_bot(event):
    """Mengaktifkan bot selama 1 bulan."""
    global bot_aktif, bot_expiry
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    bot_aktif = True
    bot_expiry = datetime.now() + timedelta(days=30)
    logging.info("✅ Bot diaktifkan oleh owner.")
    await event.respond("✅ **Bot telah diaktifkan** dan akan bekerja selama **1 bulan**.")

@bot.on(events.NewMessage(pattern="/unak"))
async def matikan_bot(event):
    """Mematikan bot sepenuhnya."""
    global bot_aktif
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    bot_aktif = False
    logging.info("❌ Bot dimatikan oleh owner.")
    await event.respond("❌ **Bot telah dimatikan** dan tidak akan merespons perintah.")

@bot.on(events.NewMessage(pattern="/kontrol"))
async def kontrol_bot(event):
    """Menampilkan tombol kontrol bot (ON/OFF)."""
    if event.sender_id != OWNER_ID and event.sender_id not in admin_list:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    
    keyboard = [
        [Button.inline("✅ ON", b"on"), Button.inline("❌ OFF", b"off")]
    ]
    await event.respond("🔹 **Kontrol Bot:** Aktifkan atau matikan bot.", buttons=keyboard)

@bot.on(events.CallbackQuery)
async def button_callback(event):
    """Mengontrol bot dengan tombol inline."""
    global bot_aktif
    if event.data == b"on":
        bot_aktif = True
        await event.edit("✅ **Bot telah diaktifkan.**")
    elif event.data == b"off":
        bot_aktif = False
        await event.edit("❌ **Bot telah dimatikan.**")

@bot.on(events.NewMessage(pattern="/ceklog"))
async def kirim_log(event):
    """Mengirim file log ke pemilik bot."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    try:
        await bot.send_file(event.chat_id, "logs/bot.log")
        logging.info("📤 Log dikirim ke owner.")
    except Exception as e:
        await event.respond("❌ Gagal mengirim log.")
        logging.error(f"⚠️ Error mengirim log: {e}")

# Menjalankan bot dengan event loop yang benar
async def main():
    logging.info("🚀 Bot telah berjalan...")
    await asyncio.gather(bot.run_until_disconnected(), run_schedule())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
