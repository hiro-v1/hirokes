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
owner_id = 123456789  # Ganti dengan ID pemilik bot
bot_expiry = None

# Membersihkan log setiap 7 hari sekali
schedule.every(7).days.do(clean_logs)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    """Menampilkan pesan sambutan bot."""
    text = "Hallo saya adalah Hirokes, yang bisa membantu mengamankan GC Anda dari spamer.\nTambahkan saya dan jadikan admin.\nTekan /help untuk bantuan."
    await message.reply_text(text)

@app.on_message(filters.command("help") & filters.private)
async def help_handler(client, message):
    """Menampilkan daftar perintah bantuan."""
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
    
    **Bot harus diaktifkan dengan /aktifbt sebelum dapat digunakan silahkan hubungi @hiro_v1.**
    """
    await message.reply_text(help_text)

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

@app.on_message(filters.command("dfadmin") & filters.user(owner_id))
async def tambah_admin(client, message):
    """Menambahkan admin bot."""
    if message.reply_to_message:
        admin_id = message.reply_to_message.from_user.id
        admin_list.append(admin_id)
        logging.info(f"Admin ditambahkan: {admin_id}")
        await message.reply_text(f"✅ Pengguna {admin_id} telah menjadi admin bot.")

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

@app.on_message(filters.command("bl") & filters.user(admin_list))
async def tambah_blacklist(client, message):
    """Menambahkan kata ke daftar kata terlarang."""
    if message.reply_to_message:
        word = message.reply_to_message.text.lower()
        add_banned_word(word)
        logging.info(f"Kata terlarang ditambahkan: {word}")
        await message.reply_text(f"✅ Kata '{word}' telah ditambahkan ke blacklist.")

@app.on_message(filters.command("inbl") & filters.user(admin_list))
async def blokir_pengguna(client, message):
    """Memblokir pengguna agar semua pesannya dihapus."""
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        add_banned_word(str(user_id))  # Simpan sebagai string
        logging.info(f"Pengguna {user_id} diblokir.")
        await message.reply_text(f"🚫 Pengguna {user_id} telah diblokir.")

@app.on_message(filters.command("unbl") & filters.user(admin_list))
async def hapus_blokir(client, message):
    """Menghapus pengguna dari daftar blokir."""
    if len(message.command) > 1:
        user_id = message.command[1]
        remove_banned_word(user_id)
        logging.info(f"Pengguna {user_id} dibebaskan dari blokir.")
        await message.reply_text(f"✅ Pengguna {user_id} telah dibebaskan.")

@app.on_message(filters.command("ceklog") & filters.user(owner_id))
async def kirim_log(client, message):
    """Mengirim file log ke pemilik bot."""
    try:
        await message.reply_document("logs/bot.log")
        logging.info("Log dikirim ke owner.")
    except Exception as e:
        await message.reply_text("❌ Gagal mengirim log.")
        logging.error(f"Error mengirim log: {e}")

# Jalankan bot & scheduler untuk membersihkan log
if __name__ == "__main__":
    logging.info("Bot telah berjalan...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Cek setiap 60 detik
    app.run()
