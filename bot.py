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
    add_banned_word, remove_banned_word, get_banned_words,
    banned_words, banned_users, get_admin_groups
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
if os.path.exists("hirokesbot.session"):
    os.remove("hirokesbot.session")

bot = TelegramClient("hirokesbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Memuat daftar admin dan pengguna yang diblokir dari database
admin_list = get_admins()
banned_users = get_banned_users()
banned_words_set = get_banned_words()

def is_admin_or_owner(user_id):
    return user_id == OWNER_ID or user_id in admin_list
   
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
    
    global admin_list
    admin_list = get_admins()  # Ambil ulang daftar admin dari database setiap kali perintah dijalankan
    
    # Pastikan OWNER_ID selalu memiliki akses
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
        logging.info("📤 Log dikirim ke owner @hiro_v1.") 
    except Exception as e:
        await event.respond("❌ Gagal mengirim log.")         
        logging.error(f"⚠️ Error mengirim log: {e}")  

@bot.on(events.NewMessage())
async def message_handler(event):
    """Memeriksa pesan yang masuk ke grup jika bot dalam kondisi aktif."""
    if not bot_aktif:
        return  # Jika bot tidak aktif, abaikan semua pesan

    user_id = event.sender_id

    # Skip deletion if the user is an admin or the owner
    if is_admin_or_owner(user_id):
        return

    # Jika pengguna dalam daftar blokir, hapus pesan mereka
    if user_id in banned_users:
        await event.delete()
        logging.info(f"🚫 Pesan dari {user_id} dihapus karena pengguna ini diblokir.")
        return

    text = event.message.text
    if await check_message(text) or contains_restricted_chars(text):
        await event.delete()
        notification_message = await event.respond("⚠️ **hapus aja ah Pesannya Alay.**")
        await asyncio.sleep(5)
        await notification_message.delete()
        logging.info(f"🛑 Pesan dari {event.sender_id} dihapus karena melanggar aturan.")
    elif text.lower().startswith("bot"):
        response = ai_response(text)
        await event.respond(response)
        logging.info(f"🤖 Bot merespons {event.sender_id} dengan AI.")
        
@bot.on(events.NewMessage(pattern="/adm"))
async def tambah_admin(event):
    """Menambahkan admin yang dapat mengontrol bot."""
    
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id

        if user_id == OWNER_ID:
            return await event.respond("⚠️ Pemilik bot sudah memiliki akses penuh.")

        if user_id not in admin_list:
            add_admin(user_id)
            admin_list.add(user_id)
            logging.info(f"✅ Admin ditambahkan: {user_id}")
            await event.respond(f"✅ **Admin {user_id} telah ditambahkan** dan dapat menggunakan `/kontrol`.")
        else:
            await event.respond("⚠️ Pengguna ini sudah menjadi admin.")
    else:
        await event.respond("❌ Gunakan perintah ini dengan mereply pesan pengguna.")


@bot.on(events.NewMessage(pattern="/unadm"))
async def hapus_admin(event):
    """Menghapus admin dari daftar kontrol bot."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id
        if user_id in admin_list:
            remove_admin(user_id)
            admin_list.remove(user_id)
            logging.info(f"❌ Admin dihapus: {user_id}")
            await event.respond(f"❌ **Admin {user_id} telah dihapus dari daftar kontrol.**")
        else:
            await event.respond("⚠️ Pengguna ini bukan admin.")
    else:
        await event.respond("❌ Gunakan perintah ini dengan mereply pesan pengguna.")


@bot.on(events.NewMessage(pattern="/bl"))
async def tambah_kata_terlarang(event):
    """Menambah kata terlarang ke dalam database."""
    global banned_words_set
    if event.sender_id != OWNER_ID and event.sender_id not in admin_list:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    if event.is_reply:
        replied_message = await event.get_reply_message()
        word = replied_message.text
    else:
        word = event.message.text.replace("/bl", "").strip()
    if word:
        add_banned_word(word)
        banned_words_set.add(word)
        logging.info(f"⚠️ Kata terlarang ditambahkan: {word}")
        await event.respond(f"⚠️ **Kata terlarang \"{word}\" telah ditambahkan.**")
    else:
        await event.respond("❌ Gunakan perintah ini dengan mereply pesan atau mengetikkan kata yang ingin dilarang.")

@bot.on(events.NewMessage(pattern="/inbl"))
async def tambah_pengguna_blacklist(event):
    """Menambahkan pengguna ke daftar blacklist."""
    global banned_users
    if event.sender_id != OWNER_ID and event.sender_id not in admin_list:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id

        if user_id in banned_users:
            return await event.respond("⚠️ Pengguna ini sudah diblokir.")

        add_banned_user(user_id)  # Tambahkan ke database
        banned_users = get_banned_users()  # Perbarui daftar blokir dari database

        logging.info(f"🚫 Pengguna diblokir: {user_id}")
        await event.respond(f"🚫 **Pengguna {user_id} telah diblokir.**")
    else:
        await event.respond("❌ Gunakan perintah ini dengan mereply pesan pengguna.")


@bot.on(events.NewMessage(pattern="/unbl"))
async def hapus_pengguna_blacklist(event):
    """Menghapus pengguna dari daftar blacklist."""
    global banned_users

    if event.sender_id != OWNER_ID and event.sender_id not in admin_list:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if event.is_reply:
        replied_user = await event.get_reply_message()
        user_id = replied_user.sender_id

        if user_id not in banned_users:
            return await event.respond("⚠️ Pengguna ini tidak ada dalam daftar blacklist.")

        remove_banned_user(user_id)  # Hapus dari database
        banned_users = get_banned_users()  # Perbarui daftar blacklist dari database

        logging.info(f"❌ Pengguna dihapus dari blacklist: {user_id}")
        await event.respond(f"❌ **Pengguna {user_id} telah dihapus dari daftar blacklist.**")
    else:
        await event.respond("❌ Gunakan perintah ini dengan mereply pesan pengguna.")

@bot.on(events.NewMessage(pattern="/bc"))
async def broadcast(event):
    """Mengirim pesan ke semua grup tempat bot menjadi admin, lalu menghapusnya setelah 30 detik."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    # Ambil teks broadcast
    text = event.message.text.replace("/bc", "").strip()
    if not text:
        return await event.respond("⚠️ Gunakan perintah ini dengan mengetikkan pesan setelah /bc.")

    # Ambil daftar grup di mana bot adalah admin
    async for dialog in bot.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            try:
                chat = await bot.get_entity(dialog.id)
                permissions = await bot.get_permissions(chat, bot.me)
                
                if permissions.is_admin:  # Pastikan bot adalah admin di grup ini
                    message = await bot.send_message(chat, f"📢 **Broadcast:** {text}")

                    # Hapus pesan setelah 30 detik
                    await asyncio.sleep(30)
                    await message.delete()
            except Exception as e:
                logging.error(f"❌ Gagal mengirim broadcast ke {dialog.name}: {e}")

    await event.respond("✅ **Pesan broadcast telah dikirim ke semua grup.**")

@bot.on(events.NewMessage(pattern="/gc"))
async def list_admin_groups(event):
    """Menampilkan daftar grup yang menjadikan bot sebagai admin."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    
    groups = get_admin_groups()
    
    if not groups:
        return await event.respond("📭 **Bot tidak menjadi admin di grup mana pun.**")

    message = "📋 **Daftar Grup Admin:**\n"
    for idx, group in enumerate(groups, start=1):
        message += f"{idx}. {group['chat_name']} (ID: `{group['chat_id']}`)\n"
    
    await event.respond(message)

@bot.on(events.NewMessage(pattern="/bc"))
async def broadcast_message(event):
    """Mengirim pesan ke semua grup di mana bot adalah admin dan menghapusnya setelah 30 detik."""
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if not event.is_reply:
        return await event.respond("⚠️ **Gunakan perintah ini dengan mereply pesan yang ingin disiarkan.**")
    
    replied_message = await event.get_reply_message()
    groups = get_admin_groups()

    if not groups:
        return await event.respond("📭 **Bot tidak menjadi admin di grup mana pun.**")

    message = f"📢 **Pesan Siaran dari {event.sender.first_name}:**\n\n{replied_message.text}"

    for group in groups:
        try:
            sent_message = await bot.send_message(group["chat_id"], message)
            await asyncio.sleep(1)  # Hindari rate limit
            await asyncio.sleep(60)  # Hapus pesan setelah 30 detik
            await bot.delete_messages(group["chat_id"], sent_message.id)
        except Exception as e:
            logging.error(f"⚠️ Gagal mengirim broadcast ke {group['chat_name']} ({group['chat_id']}): {e}")

    await event.respond("✅ **Pesan telah dikirim ke semua grup admin dan akan dihapus dalam 30 detik.**")
# Tambahkan variabel untuk menyimpan jumlah pelanggaran pengguna
mention_warnings = {}

@bot.on(events.NewMessage())
async def message_handler(event):
    """Memeriksa pesan masuk, menangani blacklist, dan membalas pesan dengan AI."""
    if not bot_aktif:
        return  # Jika bot tidak aktif, abaikan semua pesan

    user_id = event.sender_id
    text = event.message.text.lower()

    # Jika pengguna dalam daftar blokir, hapus pesan mereka
    if user_id in banned_users:
        await event.delete()
        logging.info(f"🚫 Pesan dari {user_id} dihapus karena pengguna ini diblokir.")
        return

    # Periksa kata terlarang
    if await check_message(text) or contains_restricted_chars(text):
        await event.delete()
        notification_message = await event.respond("⚠️ **hapus aja ah Alay.**")
        await asyncio.sleep(3)
        await notification_message.delete()
        logging.info(f"🛑 Pesan dari {user_id} dihapus karena mengandung kata terlarang.")
        return

    # Jika ada mention username
    if "@" in text:
        mentioned_user = text.split("@")[1].split()[0]
        try:
            participants = await bot(GetParticipants(event.chat_id, filter=ChannelParticipantsSearch(mentioned_user)))
            if not participants.users:
                await event.delete()
                mention_warnings[user_id] = mention_warnings.get(user_id, 0) + 1

                if mention_warnings[user_id] == 1:
                    warning_message = await event.respond(f"⚠️ {event.sender.first_name}, tolong undang orang yang kamu mention.")
                elif mention_warnings[user_id] == 2:
                    warning_message = await event.respond(f"⚠️ Saya sudah memperingatkan, jika terus berlanjut saya akan memblokir Anda.")
                else:
                    add_banned_user(user_id)
                    banned_users = get_banned_users()  # Perbarui daftar blokir
                    logging.info(f"🚫 Pengguna diblokir: {user_id}")
                    await event.respond(f"🚫 **{event.sender.first_name} telah diblokir karena pelanggaran berulang.**")
                    return

                await asyncio.sleep(5)
                await warning_message.delete()
                return
        except Exception:
            pass

    # **Respons AI Otomatis**
    if text.startswith("/ask"):
        query = text.replace("/ask", "").strip()
        response = ai_response(query) if query else "Gunakan `/ask` diikuti pertanyaan Anda."
    else:
        response = simple_ai_response(text)

    # Jika bot tidak memahami, berikan respon "Maksudnya?"
    if response in ["", None, " "]:
        response = "Maksudnya?"
    await event.reply(response)

async def main():
    logging.info("🚀 Bot telah berjalan...")
    await asyncio.gather(bot.run_until_disconnected(), run_schedule())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
