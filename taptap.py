import os
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
balances_file = "balances.json"

# Загружаем баланс
if os.path.exists(balances_file):
    with open(balances_file, "r") as f:
        balances = json.load(f)
else:
    balances = {}

user_games = {}

class MineGame:
    def __init__(self, bet, num_mines):
        self.bet = bet
        self.num_mines = num_mines
        self.board_size = 5
        self.total_cells = self.board_size * self.board_size
        self.opened = set()
        self.mines = set(random.sample(range(self.total_cells), num_mines))
        self.won = False

    def open_cell(self, cell_index):
        if cell_index in self.opened or self.won:
            return None, False
        self.opened.add(cell_index)
        if cell_index in self.mines:
            return "💣", True
        else:
            return "💎", False

    def calc_multiplier(self):
        diamonds = len(self.opened)
        if diamonds == 0:
            return 0
        return round(1.1 ** diamonds, 2)

    def get_grid(self):
        grid = []
        for i in range(self.total_cells):
            if i in self.opened:
                grid.append("💎" if i not in self.mines else "💣")
            else:
                grid.append("⬜")
        return grid

def save_balances():
    with open(balances_file, "w") as f:
        json.dump(balances, f)

def build_mine_grid(user_id):
    game = user_games[user_id]
    grid = []
    for row in range(5):
        buttons = []
        for col in range(5):
            i = row * 5 + col
            text = game.get_grid()[i]
            buttons.append(InlineKeyboardButton(text, callback_data=f"mine_{i}"))
        grid.append(buttons)
    grid.append([InlineKeyboardButton("💰 Забрать", callback_data="mine_cashout")])
    return InlineKeyboardMarkup(grid)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in balances:
        balances[user_id] = 100  # стартовый баланс
        save_balances()
    await update.message.reply_text("👋 Привет! Используй /balance, /mine")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bal = balances.get(user_id, 0)
    await update.message.reply_text(f"💰 Твой баланс: {bal} монет")

async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in balances or balances[user_id] < 10:
        await update.message.reply_text("❌ Недостаточно монет (минимум 10)")
        return

    bet = 10
    num_mines = 5
    balances[user_id] -= bet
    user_games[user_id] = MineGame(bet, num_mines)
    save_balances()

    await update.message.reply_text("💣 Игра началась! Выбери клетку:", reply_markup=build_mine_grid(user_id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
 import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_balance, update_balance

# Сохраняем состояние пользователя
mine_sessions = {}
tap_counts = {}

MINE_COUNT = 5
GRID_SIZE = 5

# Команда /mine
def get_mine_markup():
    keyboard = []
    for i in range(GRID_SIZE):
        row = []
        for j in range(GRID_SIZE):
            row.append(InlineKeyboardButton("⬜", callback_data=f"open_{i}_{j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start_mine_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("💣 Введите сумму ставки (например, 10):")
    context.user_data['awaiting_bet'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('awaiting_bet'):
        if not text.isdigit():
            await update.message.reply_text("Введите число!")
            return

        bet = int(text)
        balance = get_balance(user_id)

        if bet > balance:
            await update.message.reply_text("Недостаточно монет!")
            return

        # списываем ставку
        update_balance(user_id, -bet)

        # инициализируем игру
        mines = set()
        while len(mines) < MINE_COUNT:
            i = random.randint(0, GRID_SIZE - 1)
            j = random.randint(0, GRID_SIZE - 1)
            mines.add((i, j))

        mine_sessions[user_id] = {
            'bet': bet,
            'opened': set(),
            'mines': mines
        }

        context.user_data['awaiting_bet'] = False
        await update.message.reply_text("💎 Игра началась! Открывайте ячейки:", reply_markup=get_mine_markup())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in mine_sessions:
        await query.answer("Сначала начни игру командой /mine")
        return

    data = query.data
    if data.startswith("open_"):
        _, i, j = data.split("_")
        i, j = int(i), int(j)

        session = mine_sessions[user_id]
        key = (i, j)

        if key in session['opened']:
            await query.answer("Уже открыто")
            return

        session['opened'].add(key)

        if key in session['mines']:
            await query.edit_message_text("💥 Бум! Ты попал на мину.")
            mine_sessions.pop(user_id)
        else:
            # Выигрыш за ячейку = bet * множитель (например, 0.25)
            multiplier = 0.25
            reward = int(session['bet'] * multiplier)
            update_balance(user_id, reward)
            await query.answer(f"+{reward} монет!")
            await query.edit_message_reply_markup(reply_markup=update_markup(session))

            if len(session['opened']) == (GRID_SIZE * GRID_SIZE - MINE_COUNT):
                await query.edit_message_text("🎉 Ты открыл все алмазы и победил!")
                mine_sessions.pop(user_id)

def update_markup(session):
    keyboard = []
    for i in range(GRID_SIZE):
        row = []
        for j in range(GRID_SIZE):
            if (i, j) in session['opened']:
                row.append(InlineKeyboardButton("💎", callback_data="none"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"open_{i}_{j}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# Команда /tap
async def tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tap_counts[user_id] = tap_counts.get(user_id, 0) + 1
    update_balance(user_id, 1)  # 1 монета за тап
    await update.message.reply_text(f"💰 Вы нажали {tap_counts[user_id]} раз. Баланс: {get_balance(user_id)} монет.")
