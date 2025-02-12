import logging
from pyrogram import Client, filters
from config import BOT_TOKEN, API_ID, API_HASH
from modules.moderation import check_message
from modules.ai import ai_response

# Logging untuk memantau aktivitas bot
logging.basicConfig(level=logging.INFO)

# Inisialisasi bot
app = Client("hirokesbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handler untuk memproses pesan masuk
@app.on_message(filters.group & filters.text)
async def message_handler(client, message):
    if await check_message(message):
        await message.delete()
        await message.reply_text("Maaf pesan anda dilarang", quote=True)
    
    # Integrasi AI untuk membalas pesan tertentu
    elif message.text.lower().startswith("bot"):
        response = ai_response(message.text)
        await message.reply_text(response, quote=True)

# Menjalankan bot
if __name__ == "__main__":
    logging.info("Bot telah berjalan...")
    app.run()
