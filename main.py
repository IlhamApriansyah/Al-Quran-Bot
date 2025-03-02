import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    filters,
)
import requests
import database

# Token bot dari BotFather
TOKEN = "Gunakan token sendiri"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State untuk ConversationHandler
INPUT_SURAH, INPUT_AYAT = range(2)

# Command: /start
async def start(update: Update, context: CallbackContext):
    # Buat tombol reply keyboard
    keyboard = [
        ["/start", "/baca"],
        ["/penanda"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Assalamu'alaikum! Selamat datang di Bot Qur'an. Pilih opsi di bawah:",
        reply_markup=reply_markup
    )

# Command: /baca
async def baca(update: Update, context: CallbackContext):
    await update.message.reply_text("Silakan masukkan nomor surah:")
    return INPUT_SURAH

# Handler untuk menerima nomor surah
async def input_surah(update: Update, context: CallbackContext):
    surah_number = update.message.text
    if surah_number.isdigit() and 1 <= int(surah_number) <= 114:
        context.user_data['surah_number'] = surah_number
        await update.message.reply_text("Silakan masukkan nomor ayat:")
        return INPUT_AYAT
    else:
        await update.message.reply_text("Nomor surah tidak valid. Harap masukkan nomor antara 1 dan 114.")
        return ConversationHandler.END
    
# Callback: Baca penanda
async def read_bookmark(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    surah_number = int(data[1])
    verse_number = int(data[2])
    
# Handler untuk menerima nomor ayat
async def input_ayat(update: Update, context: CallbackContext):
    verse_number = update.message.text
    surah_number = context.user_data.get('surah_number')
    
    if verse_number.isdigit():

        # Ambil detail surah
        surah_detail = get_surah_detail(surah_number)
        if surah_detail:
            await update.message.reply_text(f"Detail Surah:\n"
                                          f"Nama: {surah_detail['name']}\n"
                                          f"Jumlah Ayat: {surah_detail['numberOfAyahs']}\n"
                                          f"Tempat Turun: {surah_detail['revelationType']}")

        # Ambil ayat
        response = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_number}:{verse_number}/id.indonesian")
        if response.status_code == 200:
            data = response.json()
            ayat = data['data']['text']
            await update.message.reply_text(f"QS {surah_number}:{verse_number}\n\n{ayat}")
            
            # Tombol inline untuk menandai ayat
            keyboard = [
                [InlineKeyboardButton("Tandai Ayat", callback_data=f"bookmark_{surah_number}_{verse_number}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Pilih opsi:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Gagal mengambil ayat. Silakan coba lagi.")
    else:
        await update.message.reply_text("Nomor ayat tidak valid. Harap masukkan angka.")
    
    return ConversationHandler.END

# Fungsi untuk mendapatkan detail surah
def get_surah_detail(surah_number):
    response = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_number}")
    if response.status_code == 200:
        data = response.json()
        return data['data']
    return None

# Callback: Tandai ayat
async def bookmark(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    surah_number = int(data[1])
    verse_number = int(data[2])
    user_id = query.from_user.id
    
    # Ambil nama surah
    surah_detail = get_surah_detail(surah_number)
    if surah_detail:
        surah_name = surah_detail['name']
    else:
        surah_name = f"Surah {surah_number}"
    
    # Simpan penanda ke database
    database.add_bookmark(user_id, surah_number, verse_number, surah_name)
    await query.edit_message_text(f"Ayat {surah_name} ({surah_number}:{verse_number}) telah ditandai.")

# Command: /penanda
async def penanda(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    bookmarks = database.get_bookmarks(user_id)
    
    if bookmarks:
        # Buat tombol inline untuk setiap penanda
        keyboard = []
        for bookmark in bookmarks:
            button_text = f"{bookmark['surah_name']} ({bookmark['surah_number']}:{bookmark['verse_number']})"
            callback_data = f"read_{bookmark['surah_number']}_{bookmark['verse_number']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Daftar Penanda Anda:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Anda belum memiliki penanda.")

# Error handler
async def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error {context.error}')

# Set menu perintah
async def set_commands(application: Application):
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("baca", "Baca ayat Qur'an"),
        BotCommand("penanda", "Lihat daftar penanda"),
    ]
    await application.bot.set_my_commands(commands)

# Main function
def main():
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler untuk /baca
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("baca", baca)],
        states={
            INPUT_SURAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_surah)],
            INPUT_AYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_ayat)],
        },
        fallbacks=[],
    )

    # Tambahkan handler
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("penanda", penanda))
    application.add_handler(CallbackQueryHandler(bookmark, pattern="^bookmark_"))
    application.add_handler(CallbackQueryHandler(read_bookmark, pattern="^read_"))

    # Set perintah menu
    application.run_polling()

if __name__ == '__main__':
    main()