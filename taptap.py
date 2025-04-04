from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import os
import json
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

BALANCES_FILE = "balances.json"

# Загружаем баланс из файла
def load_balances():
    if not os.path.exists(BALANCES_FILE):
        return {}
    with open(BALANCES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# Сохраняем баланс в файл
def save_balances(balances):
    with open(BALANCES_FILE, "w", encoding="utf-8") as file:
        json.dump(balances, file, ensure_ascii=False, indent=4)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Тапни меня!", callback_data='tap')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Салам заебал! Нажми кнопку ниже, чтобы заработать кеш!",
        reply_markup=reply_markup
    )

# Обработка нажатия на кнопку
async def tap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user

    balances = load_balances()
    user_id = str(user.id)
    coins = random.randint(1, 10)

    balances[user_id] = balances.get(user_id, 0) + coins
    save_balances(balances)

    await query.edit_message_text(
        text=f"🎉 {user.first_name}, вы заработали {coins} мемкоинов!\n"
             f"💰 Всего у вас: {balances[user_id]} мемкоинов.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Тапни снова!", callback_data='tap')]
        ])
    )

# Команда /balance — показать текущий баланс
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    balances = load_balances()
    user_balance = balances.get(str(user.id), 0)
    await update.message.reply_text(f"💼 Ваш баланс: {user_balance} мемкоинов.")

# Главная функция
def main():
    app = Application.builder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CallbackQueryHandler(tap, pattern="tap"))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
