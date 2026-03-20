import logging
import datetime
import os
from datetime import timezone, timedelta
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# --- МИНИ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (ЧТОБЫ НЕ БЫЛО TIMED OUT) ---
keep_alive_app = Flask('')

@keep_alive_app.route('/')
def home():
    return "Бот запущен и работает!"

def run():
    # Render передает порт в переменную окружения PORT, по умолчанию 8080
    port = int(os.environ.get('PORT', 8080))
    keep_alive_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
# ------------------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMERGENCY_PHONE = "+77771838479" 

SPECIALISTS = {
    'suggestion': 5264345588,   
    'help': 5264345588,          
    'anonymous': 1086304129,    
    'psychologist': 1198800670, 
    'emergency': 777888999     
}

SELECT_LANG, SELECT_ACTION, ASK_NAME, ASK_CLASS, ASK_MESSAGE = range(5)

MESSAGES = {
    'kz': {
        'welcome': "Сәлем! 👋\nБұл бот арқылы сіз:\n🔹 Мектепке ұсыныс жібере аласыз\n🔹 Қиын жағдайда көмек сұрай аласыз\n\nТөмендегі батырмалардың бірін таңдаңыз:",
        'btn_suggest': "📌 Ұсыныс", 'btn_help': "🤝 Көмек", 'btn_anon': "🕵️‍♂️ Анонимді", 
        'btn_psych': "🧠 Психолог", 'btn_emerg': "🚨 Жылдам көмек",
        'ask_name': "Атыңызды жазыңыз:", 'ask_class': "Сынып:", 'ask_msg': "Хабарламаңызды жазыңыз:", 'success': "✅ Жіберілді!",
        'emerg_text': "🚨 <b>Шұғыл байланыс / Экстренная связь:</b>\n\nҚоңырау шалу үшін нөмірді басыңыз!\nНажмите на номер, чтобы позвонить:\n"
    },
    'ru': {
        'welcome': "Привет! 👋\nЧерез этот бот вы можете:\n🔹 Отправить предложение школе\n🔹 Попросить о помощи в трудной ситуации\n\nВыберите одну из кнопок ниже:",
        'btn_suggest': "📌 Предложение", 'btn_help': "🤝 Помощь", 'btn_anon': "🕵️‍♂️ Анонимно", 
        'btn_psych': "🧠 Психолог", 'btn_emerg': "🚨 Срочная помощь",
        'ask_name': "Напишите ваше имя:", 'ask_class': "Класс:", 'ask_msg': "Напишите ваше сообщение:", 'success': "✅ Отправлено!",
        'emerg_text': "🚨 <b>Шұғыл байланыс / Экстренная связь:</b>\n\nҚоңырау шалу үшін нөмірді басыңыз!\nНажмите на номер, чтобы позвонить:\n"
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Қазақша 🇰🇿", callback_data='lang_kz')], [InlineKeyboardButton("Русский 🇷🇺", callback_data='lang_ru')]]
    await update.message.reply_text("Тілді таңдаңыз / Выберите язык:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_LANG

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = 'kz' if query.data == 'lang_kz' else 'ru'
    context.user_data['lang'] = lang
    keyboard = [[InlineKeyboardButton(MESSAGES[lang]['btn_suggest'], callback_data='suggestion')],
                [InlineKeyboardButton(MESSAGES[lang]['btn_help'], callback_data='help')],
                [InlineKeyboardButton(MESSAGES[lang]['btn_anon'], callback_data='anonymous')],
                [InlineKeyboardButton(MESSAGES[lang]['btn_psych'], callback_data='psychologist')],
                [InlineKeyboardButton(MESSAGES[lang]['btn_emerg'], callback_data='emergency')]]
    await query.message.edit_text(MESSAGES[lang]['welcome'], reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'ru')
    context.user_data['type'] = query.data
    if query.data == 'emergency':
        await query.message.reply_text(f"{MESSAGES[lang]['emerg_text']} {EMERGENCY_PHONE}", parse_mode='HTML')
        return ConversationHandler.END
    if query.data == 'anonymous':
        await query.message.reply_text(MESSAGES[lang]['ask_msg'])
        return ASK_MESSAGE
    await query.message.reply_text(MESSAGES[lang]['ask_name'])
    return ASK_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    lang = context.user_data.get('lang', 'ru')
    await update.message.reply_text(MESSAGES[lang]['ask_class'])
    return ASK_CLASS

async def get_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['class'] = update.message.text
    lang = context.user_data.get('lang', 'ru')
    await update.message.reply_text(MESSAGES[lang]['ask_msg'])
    return ASK_MESSAGE

async def send_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'ru')
    u = context.user_data
    target_id = SPECIALISTS.get(u.get('type'))
    action_type = u.get('type')
    
    # Время Казахстана (UTC+5)
    tz_kz = timezone(timedelta(hours=5))
    dt_string = datetime.datetime.now(tz_kz).strftime("%d.%m.%Y | %H:%M")

    name = u.get('name', 'Анонимно / Анонимді')
    u_class = u.get('class', '---')

    report = (f"📩 <b>ӨТІНІШ / ОБРАЩЕНИЕ: {action_type.upper()}</b>\n"
              f"📅 <b>Уақыты / Время:</b> {dt_string}\n"
              f"────────────────────\n"
              f"👤 <b>Имя / Аты:</b> {name}\n"
              f"🏫 <b>Класс / Сынып:</b> {u_class}\n"
              f"📝 <b>Текст / Мәтін:</b> {update.message.text}\n"
              f"────────────────────\n"
              f"👇 <b>Чтобы ответить, нажмите на имя автора сообщения ниже:</b>")
    
    try:
        await context.bot.send_message(chat_id=target_id, text=report, parse_mode='HTML')
        await context.bot.forward_message(chat_id=target_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await update.message.reply_text(MESSAGES[lang]['success'])
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("Ошибка отправки / Жіберу қатесі")
    return ConversationHandler.END

if __name__ == '__main__':
    keep_alive()  # <--- ВОТ ЭТА СТРОКА ИСПРАВЛЯЕТ TIMED OUT
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(set_lang)],
            SELECT_ACTION: [CallbackQueryHandler(handle_action)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
            ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_final)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    app.add_handler(conv)
    app.run_polling()
