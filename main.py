import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
server = Flask('')

@server.route('/')
def home():
    return "I'm alive!"

def run():
    server.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# --------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Берем токен из переменных окружения (безопасно)
BOT_TOKEN = os.getenv("BOT_TOKEN")
EMERGENCY_PHONE = "+77001234567" 

SPECIALISTS = {
    'suggestion': 495342466,   
    'help': 987654321,          
    'anonymous': 111222333,    
    'psychologist': 444555666, 
    'emergency': 777888999     
}

SELECT_LANG, SELECT_ACTION, ASK_NAME, ASK_CLASS, ASK_MESSAGE = range(5)

MESSAGES = {
    'kz': {
        'welcome': "Сәлем! 👋\nБұл бот арқылы ұсыныс жіберуге немесе көмек сұрауға болады.\nТаңдаңыз:",
        'btn_suggest': "📌 Ұсыныс", 'btn_help': "🤝 Көмек", 'btn_anon': "🕵️‍♂️ Анонимді", 
        'btn_psych': "🧠 Психолог", 'btn_emerg': "🚨 Жылдам көмек",
        'ask_name': "Атыңыз:", 'ask_class': "Сынып:", 'ask_msg': "Мәтін:", 'success': "✅ Жіберілді!",
        'emerg_text': "🚨 *Шұғыл байланыс:*\n\nҚоңырау шалу үшін нөмірді басыңыз:\n"
    },
    'ru': {
        'welcome': "Привет! 👋\nЭтот бот поможет отправить предложение или попросить о помощи.\nВыберите:",
        'btn_suggest': "📌 Предложение", 'btn_help': "🤝 Помощь", 'btn_anon': "🕵️‍♂️ Анонимно", 
        'btn_psych': "🧠 Психолог", 'btn_emerg': "🚨 Срочная помощь",
        'ask_name': "Ваше имя:", 'ask_class': "Класс:", 'ask_msg': "Текст:", 'success': "✅ Отправлено!",
        'emerg_text': "🚨 *Экстренная связь:*\n\nНажмите на номер, чтобы позвонить:\n"
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🇰🇿 Қазақша", callback_data='lang_kz'), InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')]]
    await update.message.reply_text("Тілді таңдаңыз / Выберите язык:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_LANG

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = 'kz' if query.data == 'lang_kz' else 'ru'
    context.user_data['lang'] = lang
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['btn_suggest'], callback_data='suggestion')],
        [InlineKeyboardButton(MESSAGES[lang]['btn_help'], callback_data='help')],
        [InlineKeyboardButton(MESSAGES[lang]['btn_anon'], callback_data='anonymous')],
        [InlineKeyboardButton(MESSAGES[lang]['btn_psych'], callback_data='psychologist')],
        [InlineKeyboardButton(MESSAGES[lang]['btn_emerg'], callback_data='emergency')]
    ]
    await query.message.edit_text(MESSAGES[lang]['welcome'], reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'ru')
    context.user_data['type'] = query.data
    if query.data == 'emergency':
        await query.message.reply_text(f"{MESSAGES[lang]['emerg_text']} {EMERGENCY_PHONE}", parse_mode='Markdown')
        return ConversationHandler.END
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
    user_link = f"tg://user?id={update.effective_user.id}"
    report = (f"📩 *ОБРАЩЕНИЕ: {u.get('type').upper()}*\n"
              f"👤 *Имя:* {u.get('name')}\n"
              f"🏫 *Класс:* {u.get('class')}\n"
              f"📝 *Текст:* {update.message.text}\n"
              f"🔗 [Профиль отправителя]({user_link})")
    try:
        await context.bot.send_message(chat_id=target_id, text=report, parse_mode='Markdown')
        await update.message.reply_text(MESSAGES[lang]['success'])
    except:
        await update.message.reply_text("Ошибка: Специалист не в сети.")
    return ConversationHandler.END

if __name__ == '__main__':
    keep_alive() # Запускаем веб-сервер
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(set_lang)],
            SELECT_ACTION: [CallbackQueryHandler(handle_action)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_class)],
            ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_final)],
        },
        fallbacks=[CommandHandler('start', start)]
    ))
    print("Бот запущен!")
    app.run_polling()
