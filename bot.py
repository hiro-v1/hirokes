import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from modules import check_message, contains_restricted_chars, ai_response, clean_logs
from modules.database import add_banned_word, remove_banned_word

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
admin_list = []
bot_expiry = None

# Menjadwalkan pembersihan log setiap 7 hari
schedule.every(7).days.do(clean_logs)

async def run_schedule():
    """Menjalankan schedule secara asinkron"""
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

# Handler untuk perintah /start
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    """Menampilkan pesan sambutan bot."""
    await event.respond(
        "Hallo saya adalah Hirokes, yang bisa membantu mengamankan GC Anda dari spamer.\n"
        "Tambahkan saya dan jadikan admin.\nTekan /help untuk bantuan."
    )

# Handler untuk perintah /help
@bot.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    """Menampilkan daftar perintah bot."""
    help_text = """🔹 **Daftar Perintah Bot Hirokes** 🔹
    
    **Admin & Owner Commands:**
    - /kontrol → Menampilkan tombol ON & OFF untuk mengontrol bot
    - /bl (reply text) → Menambahkan kata ke daftar kata terlarang
    - /inbl (reply user) → Memblokir pengguna agar semua pesan dihapus
    - /unbl (username) → Menghapus pengguna dari daftar blokir
    
    **Owner Commands Only:**
    - /aktifbt → Mengaktifkan bot selama 1 bulan
    - /dfadmin (reply user) → Menjadikan pengguna sebagai admin bot
    - /unak → Mematikan seluruh fungsi bot
    - /ceklog → Mengirim file log bot.log ke owner
    """
    await event.respond(help_text)

# Handler untuk mengaktifkan bot
@bot.on(events.NewMessage(pattern="/aktifbt"))
async def aktifkan_bot(event):
    """Mengaktifkan bot selama 1 bulan."""
    global bot_aktif, bot_expiry
    if event.sender_id != OWNER_ID:
        return
    bot_aktif = True
    bot_expiry = datetime.now() + timedelta(days=30)
    logging.info("Bot diaktifkan oleh owner.")
    await event.respond("✅ Bot telah diaktifkan dan akan bekerja selama 1 bulan.")

# Handler untuk mematikan bot
@bot.on(events.NewMessage(pattern="/unak"))
async def matikan_bot(event):
    """Mematikan bot sepenuhnya."""
    global bot_aktif
    if event.sender_id != OWNER_ID:
        return
    bot_aktif = False
    logging.info("Bot dimatikan oleh owner.")
    await event.respond("❌ Bot telah dimatikan. Tidak akan merespon perintah.")

# Handler untuk mengontrol bot dengan tombol inline
@bot.on(events.NewMessage(pattern="/kontrol"))
async def kontrol_bot(event):
    """Menampilkan tombol kontrol bot (ON/OFF)."""
    if event.sender_id not in admin_list:
        return
    keyboard = [
        [Button.inline("✅ ON", b"on"), Button.inline("❌ OFF", b"off")]
    ]
    await event.respond("🔹 Aktifkan atau matikan bot:", buttons=keyboard)

@bot.on(events.CallbackQuery)
async def button_callback(event):
    """Mengontrol bot dengan tombol inline."""
    global bot_aktif
    if event.data == b"on":
        bot_aktif = True
        await event.edit("✅ Bot telah diaktifkan.")
    elif event.data == b"off":
        bot_aktif = False
        await event.edit("❌ Bot telah dimatikan.")

# Handler untuk mengirim log ke owner
@bot.on(events.NewMessage(pattern="/ceklog"))
async def kirim_log(event):
    """Mengirim file log ke pemilik bot."""
    if event.sender_id != OWNER_ID:
        return
    try:
        await bot.send_file(event.chat_id, "logs/bot.log")
        logging.info("Log dikirim ke owner.")
    except Exception as e:
        await event.respond("❌ Gagal mengirim log.")
        logging.error(f"Error mengirim log: {e}")

# Handler untuk memeriksa pesan dalam grup
@bot.on(events.NewMessage())
async def message_handler(event):
    """Memeriksa pesan yang masuk ke grup jika bot dalam kondisi aktif."""
    if not bot_aktif:
        return  # Jika bot tidak aktif, abaikan semua pesan

    text = event.message.text
    if await check_message(text) or contains_restricted_chars(text):
        await event.delete()
        await event.respond("Maaf, pesan Anda mengandung karakter atau kata terlarang.")
        logging.info(f"Pesan dari {event.sender_id} dihapus karena mengandung kata terlarang.")

    elif text.lower().startswith("bot"):
        response = ai_response(text)
        await event.respond(response)
        logging.info(f"Bot merespons {event.sender_id} dengan AI.")

# Menjalankan bot
async def main():
    logging.info("Bot telah berjalan...")
    await asyncio.gather(bot.run_until_disconnected(), run_schedule())

if __name__ == "__main__":
    asyncio.run(main())
