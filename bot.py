import logging
import sys
import asyncio
import schedule
import os
import time
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon import functions, types, events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from modules.moderation import check_message, contains_restricted_chars
from modules.ai import ai_response, simple_ai_response
from modules.database import (
    add_admin, remove_admin, get_admins, 
    add_banned_user, remove_banned_user, get_banned_users,
    add_banned_word, remove_banned_word, get_banned_words,
    banned_words, banned_users, add_admin_group,
    remove_admin_group, get_admin_groups,
    add_warning, get_warnings, reset_warnings
)
from modules.log_cleaner import clean_logs
from modules.chatbot import chatbot_response
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantsSearch, ChannelParticipantsAdmins
from telethon import *

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

def update_data():
    """Perbarui daftar admin, blacklist, dan kata terlarang"""
    global admin_list, banned_users, banned_words_set, admin_groups, user_warnings
    admin_list = get_admins()
    banned_users = get_banned_users()
    banned_words_set = get_banned_words()
    admin_groups = get_admin_groups()
    user_warnings = {user_id: get_warnings(user_id) for user_id in banned_users}
    logging.info("✅ Data admin, blacklist, dan kata terlarang diperbarui.")

@bot.on(events.ChatAction)
async def track_admin_status(event):
    """Memantau jika bot menjadi admin atau dikeluarkan dari grup."""
    update_data()
    global bot_info
    chat = await event.get_chat()

    # Jika bot ditambahkan sebagai admin
    if event.added_by and event.added_by.bot and event.added_by.id == bot_info.id:
        add_admin_group(chat.id, chat.title)
        logging.info(f"📌 Bot menjadi admin di grup: {chat.title} ({chat.id})")

    # Jika bot dikeluarkan dari grup
    elif event.user_id == bot_info.id and event.user_left:
        remove_admin_group(chat.id)
        logging.info(f"❌ Bot dikeluarkan dari grup: {chat.title} ({chat.id})")

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
        
async def sync_admin_groups():
    """Memeriksa dan memperbarui daftar grup di mana bot menjadi admin."""
    logging.info("🚀 Memeriksa grup tempat bot menjadi admin...")
    update_data()
    groups = get_admin_groups()
    updated_groups = []

    for group in groups:
        try:
            chat = await bot.get_entity(group["chat_id"])
            # 🔍 Ambil daftar admin grup menggunakan GetParticipants
            participants = await bot(GetParticipants(chat, filter=ChannelParticipantsAdmins()))
            admin_ids = {user.id for user in participants.users}
            permissions = await bot.get_permissions(chat, bot.me)
            
            if bot.me.id in admin_ids:
                updated_groups.append({"chat_id": chat.id, "chat_name": chat.title})
                save_admin_group(chat.id, chat.title)  # Pastikan fungsi ini ada di database.py
                logging.info(f"✅ Bot tetap menjadi admin di grup: {chat.title} ({chat.id})")
            else:
                logging.warning(f"⚠️ Bot bukan lagi admin di grup: {chat.title} ({chat.id})")
                remove_admin_group(chat.id)  # Hapus dari database jika bukan admin
        except Exception as e:
            logging.error(f"❌ Gagal memeriksa grup {group['chat_name']} ({group['chat_id']}): {e}")
            remove_admin_group(group["chat_id"])  # Hapus dari database jika gagal diakses

    logging.info(f"✅ Sinkronisasi selesai! Bot tetap menjadi admin di {len(updated_groups)} grup.")
    return updated_groups

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
    - /ask (text) → Buat nanya ke bot
    
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
    update_data()
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
    update_data()
    global bot_aktif
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")    
    bot_aktif = False
    logging.info("❌ Bot dimatikan oleh owner.")
    await event.respond("❌ **Bot telah dimatikan** dan tidak akan merespons perintah.")

@bot.on(events.NewMessage(pattern="/kontrol"))
async def kontrol_bot(event):
    """Menampilkan tombol kontrol bot (ON/OFF)."""
    update_data()
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
    update_data()
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
    try:
        await bot.send_file(event.chat_id, "logs/bot.log")
        logging.info("📤 Log dikirim ke owner @hiro_v1.") 
    except Exception as e:
        await event.respond("❌ Gagal mengirim log.")         
        logging.error(f"⚠️ Error mengirim log: {e}")  

@bot.on(events.NewMessage(pattern="/adm"))
async def tambah_admin(event):
    """Menambahkan admin yang dapat mengontrol bot."""
    update_data()
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
    update_data()
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
    update_data()
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
    update_data()
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
    update_data()
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

@bot.on(events.NewMessage(pattern="/gc"))
async def list_admin_groups(event):
    """Menampilkan daftar grup tempat bot menjadi admin."""
    update_data()
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    groups = get_admin_groups()
    
    if not groups:
        return await event.respond("📭 **Bot tidak menjadi admin di grup mana pun.**")

    message = "📋 **Daftar Grup Tempat Bot Menjadi Admin:**\n"
    for idx, group in enumerate(groups, start=1):
        message += f"{idx}. {group['chat_name']} (ID: `{group['chat_id']}`)\n"
    
    await event.respond(message)

@bot.on(events.NewMessage(pattern="/bc"))
async def broadcast_message(event):
    """Mengirim pesan ke semua grup tempat bot menjadi admin dan menghapusnya setelah 30 detik."""
    update_data()
    if event.sender_id != OWNER_ID:
        return await event.respond("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")

    if not event.is_reply:
        return await event.respond("⚠️ **Gunakan perintah ini dengan mereply pesan yang ingin disiarkan.**")

    replied_message = await event.get_reply_message()
    groups = get_admin_groups()

    if not groups:
        return await event.respond("📭 **Bot tidak menjadi admin di grup mana pun.**")

    message_text = f"📢 **Pesan Siaran dari {event.sender.first_name}:**\n\n{replied_message.text}"
    success_count = 0
    failed_groups = []

    for group in groups:
        try:
            chat = await bot.get_entity(group["chat_id"])
            permissions = await bot.get_permissions(chat, bot.me)

            if permissions and permissions.is_admin:
                sent_message = await bot.send_message(group["chat_id"], message_text)
                success_count += 1

                await asyncio.sleep(1)  # Hindari rate limit
                await asyncio.sleep(30)  # Hapus setelah 30 detik
                await bot.delete_messages(group["chat_id"], sent_message.id)
            else:
                failed_groups.append(f"{group['chat_name']} (ID: {group['chat_id']}) - Bot bukan admin")
                remove_admin_group(group["chat_id"])  # Hapus dari database jika bot bukan admin
        except Exception as e:
            failed_groups.append(f"{group['chat_name']} (ID: {group['chat_id']}) - Error: {e}")
            logging.error(f"⚠️ Gagal mengirim broadcast ke {group['chat_name']} ({group['chat_id']}): {e}")

    report_message = f"✅ **Broadcast selesai!**\n📨 Berhasil dikirim ke **{success_count}** grup."
    if failed_groups:
        report_message += "\n⚠️ Gagal dikirim ke:\n" + "\n".join(failed_groups)

    await event.respond(report_message)

@bot.on(events.NewMessage(pattern="/ask"))
async def ask_chatgpt(event):
    """Menjawab pertanyaan dengan API ChatGPT."""
    query = event.message.text.replace("/ask", "").strip()
    
    if not query:
        return await event.respond("Gunakan `/ask` diikuti pertanyaan kamu.")

    thinking_message = await event.respond("⏳ bentar mikir dulu...")  
    response = ai_response(query)
    await bot.delete_messages(event.chat_id, thinking_message.id)
    await event.respond(response)

# Tambahkan variabel untuk menyimpan jumlah pelanggaran pengguna
mention_warnings = {}

@bot.on(events.NewMessage())
async def message_handler(event):
    """Memeriksa pesan masuk, menangani blacklist, dan merespons dengan chatbot."""
    if not bot_aktif:
        return  # Abaikan jika bot nonaktif
        
    user_id = event.sender_id    
    user_name = event.sender.first_name  # Mengambil nama pengguna
    text = event.message.text.lower()

    update_data()  # Perbarui daftar pengguna terlarang jika berubah

    # Lewati admin dan owner
    if user_id == OWNER_ID or user_id in admin_list:
        return  # Owner dan admin diabaikan

    # Hapus pesan jika pengguna diblokir
    if user_id in banned_users:
        await event.delete()
        logging.info(f"🚫 Pesan dari {user_name} dihapus (pengguna terblokir).")
        return

    # Pengecekan moderasi (kata terlarang)
    if await check_message(text) or contains_restricted_chars(text):
        await event.delete()
        warning_text = f"⚠️ gua apus ya **{user_name}** soalnya lu alay"
        notification_message = await event.respond(warning_text)
        await asyncio.sleep(5)
        await notification_message.delete()
        logging.info(f"🛑 Pesan dari {user_name} ({user_id}) dihapus (melanggar aturan).")
        return

    # **Gunakan chatbot jika tidak ada pelanggaran**
    response = chatbot_response(text)
    await event.respond(response)
    
    # Jika ada mention username
    if "@" in text:
        mentioned_user = text.split("@")[1].split()[0]
        try:
            participants = await bot(GetParticipantsRequest(
                channel=event.chat_id,
                filter=ChannelParticipantsSearch(mentioned_user),
                offset=0,
                limit=100,
                hash=0
            ))
            if not participants.users:
                await event.delete()
                add_warning(user_id)
                warnings = get_warnings(user_id)

                if warnings == 1:
                    warning_message = await event.respond(f"⚠️ {event.sender.first_name}, invit dulu orangnya buat join MOGEN.")
                elif warnings == 2:
                    warning_message = await event.respond(f"⚠️ Saya sudah memperingatkan, jika terus berlanjut saya akan memblokir Anda.")
                else:  # Jika lebih dari 2 peringatan, blokir pengguna
                   add_banned_user(user_id)
                   update_data()
                   await event.respond(f"🚫 **{event.sender.first_name} telah diblokir.**")
                   return
                    
                await asyncio.sleep(5)
                await warning_message.delete()
        except ChatAdminRequiredError:
            logging.error("❌ Bot tidak memiliki izin melihat anggota grup.")
        except Exception as e:
            logging.error(f"⚠️ Gagal memeriksa mention: {e}")


async def main():
    global bot_info
    bot_info = await bot.get_me()  # Fetch bot's information
    logging.info("🚀 Bot sedang memeriksa grup tempatnya menjadi admin...")
    await sync_admin_groups()  # Sinkronisasi grup admin saat bot dimulai
    logging.info("✅ Sinkronisasi grup admin selesai!")
    
    logging.info("🚀 Bot telah berjalan...")
    await asyncio.gather(bot.run_until_disconnected(), run_schedule())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
