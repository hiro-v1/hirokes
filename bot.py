import logging
import schedule
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, API_ID, API_HASH
from modules import check_message, contains_restricted_chars, ai_response, clean_logs
from modules.database import add_banned_word, remove_banned_word

# Konfigurasi logging
logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Inisialisasi bot
app = Client("hirokesbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Variabel kontrol bot
bot_aktif = False
admin_list = []
owner_id = 5432983527  # Ganti dengan ID pemilik bot
bot_expiry = None

# Membersihkan log setiap 7 hari sekali
schedule.every(7).days.do(clean_logs)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    """Menampilkan pesan sambutan bot."""
    text = "Hallo saya adalah Hirokes, yang bisa membantu mengamankan GC Anda dari spamer.\nTambahkan saya dan jadikan admin.\nTekan /help untuk bantuan."
    await message.reply_text(text)

@app.on_message(filters.command("aktifbt") & filters.user(owner_id))
async def aktifkan_bot(client, message):
    """Mengaktifkan bot selama 1 bulan."""
    global bot_aktif, bot_expiry
    bot_aktif = True
    bot_expiry = datetime.now() + timedelta(days=30)
    logging.info("Bot diaktifkan oleh owner.")
    await message.reply_text("✅ Bot telah diaktifkan dan akan bekerja selama 1 bulan.")

@app.on_message(filters.command("unak") & filters.user(owner_id))
async def matikan_bot(client, message):
    """Mematikan bot sepenuhnya."""
    global bot_aktif
    bot_aktif = False
    logging.info("Bot dimatikan oleh owner.")
    await message.reply_text("❌ Bot telah dimatikan. Tidak akan merespon perintah.")

@app.on_message(filters.command("kontrol") & filters.user(admin_list))
async def kontrol_bot(client, message):
    """Menampilkan tombol kontrol bot (ON/OFF)."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ON", callback_data="on"),
         InlineKeyboardButton("❌ OFF", callback_data="off")]
    ])
    await message.reply_text("🔹 Aktifkan atau matikan bot:", reply_markup=keyboard)

@app.on_callback_query()
async def button_callback(client, callback_query):
    """Mengontrol bot dengan tombol inline."""
    global bot_aktif
    if callback_query.data == "on":
        bot_aktif = True
        await callback_query.message.edit_text("✅ Bot telah diaktifkan.")
    elif callback_query.data == "off":
        bot_aktif = False
        await callback_query.message.edit_text("❌ Bot telah dimatikan.")

@app.on_message(filters.command("ceklog") & filters.user(owner_id))
async def kirim_log(client, message):
    """Mengirim file log ke pemilik bot."""
    try:
        await message.reply_document("logs/bot.log")
        logging.info("Log dikirim ke owner.")
    except Exception as e:
        await message.reply_text("❌ Gagal mengirim log.")
        logging.error(f"Error mengirim log: {e}")

@app.on_message(filters.group & filters.text)
async def message_handler(client, message):
    """Memeriksa pesan yang masuk ke grup jika bot dalam kondisi aktif."""
    if not bot_aktif:
        return  # Jika bot tidak aktif, abaikan semua pesan

    # Periksa apakah pesan mengandung kata terlarang atau karakter spesial
    if await check_message(message) or contains_restricted_chars(message.text):
        await message.delete()
        await message.reply_text("alay lu.", quote=True)
        logging.info(f"Pesan dari {message.from_user.id} dihapus karena alay jamet.")

    elif message.text.lower().startswith("bot"):
        response = ai_response(message.text)
        await message.reply_text(response, quote=True)
        logging.info(f"Bot merespons {message.from_user.id} dengan AI.")

# Jalankan bot & scheduler untuk membersihkan log
if __name__ == "__main__":
    logging.info("Bot telah berjalan...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Cek setiap 60 detik
    app.run()
