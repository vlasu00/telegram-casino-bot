from flask import Flask, request, jsonify
import random
import sqlite3
import os
import time
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8263606127:AAGK8Cvf2mbkTM2AMCg-Mc8NDjJrIE3bu_A"

# СЕКРЕТНЫЕ НАСТРОЙКИ
ADMIN_USERNAME = "mn0_0"  # Твой Telegram username
TON_WALLET = "UQDwad48c_DV0lPJ15gmgrSoFmwE_IAJrG-tc66trbdtj9tj"  # Твой TON кошелек

class CasinoConfig:
    VIP_LEVELS = {
        1000: "🥉 БРОНЗА",
        5000: "🥈 СЕРЕБРО", 
        10000: "🥇 ЗОЛОТО",
        50000: "💎 ДИАМАНТ",
        100000: "👑 ЛЕГЕНДА"
    }
    JACKPOT_BASE = 50000

def init_db():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 5000,
            vip_level TEXT DEFAULT '👶 НОВИЧОК',
            total_wins INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            jackpots INTEGER DEFAULT 0,
            total_deposited REAL DEFAULT 0,
            total_withdrawn REAL DEFAULT 0,
            registered_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            currency TEXT,
            status TEXT,
            tx_hash TEXT,
            created_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jackpot (
            amount INTEGER DEFAULT 50000
        )
    ''')
    cursor.execute('SELECT * FROM jackpot')
    if not cursor.fetchone():
        cursor.execute('INSERT INTO jackpot (amount) VALUES (?)', (50000,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user: return None
    return {
        'user_id': user[0], 'username': user[1], 'balance': user[2],
        'vip_level': user[3], 'total_wins': user[4], 'total_games': user[5],
        'jackpots': user[6], 'total_deposited': user[7], 'total_withdrawn': user[8]
    }

def create_user(user_id, username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (user_id, username, balance, registered_date) VALUES (?, ?, ?, ?)',
        (user_id, username, 5000, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()[0]
    vip_level = "👶 НОВИЧОК"
    for threshold, level in CasinoConfig.VIP_LEVELS.items():
        if balance >= threshold: vip_level = level
    cursor.execute('UPDATE users SET vip_level = ? WHERE user_id = ?', (vip_level, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id, tx_type, amount, currency, status="completed", tx_hash=None):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO transactions (user_id, type, amount, currency, status, tx_hash, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, tx_type, amount, currency, status, tx_hash, datetime.now().isoformat())
    )
    if tx_type == "deposit" and status == "completed":
        cursor.execute('UPDATE users SET total_deposited = total_deposited + ? WHERE user_id = ?', (amount, user_id))
    elif tx_type == "withdraw" and status == "completed":
        cursor.execute('UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_jackpot():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT amount FROM jackpot')
    amount = cursor.fetchone()[0]
    conn.close()
    return amount

def update_jackpot(amount):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE jackpot SET amount = amount + ?', (amount,))
    conn.commit()
    conn.close()

def send_telegram_message(chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=data, timeout=10)
    except: pass

# СЕКРЕТНЫЕ КОМАНДЫ АДМИНА
def handle_admin_command(user_id, username, text, chat_id):
    if username != ADMIN_USERNAME:
        return False
    
    if text.startswith("/add_coins "):
        try:
            parts = text.split()
            if len(parts) == 3:
                target_username = parts[1]
                coins = int(parts[2])
                
                # Находим пользователя по username
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
                target_user = cursor.fetchone()
                
                if target_user:
                    target_user_id = target_user[0]
                    update_balance(target_user_id, coins)
                    add_transaction(target_user_id, "admin_add", coins, "COINS", "completed", f"admin_{user_id}")
                    
                    send_telegram_message(chat_id, f"✅ <b>ВЫДАНО {coins} ЗВЕЗД ⭐</b>\n\nИгроку: {target_username}\nАдмин: {username}")
                    send_telegram_message(target_user_id, f"🎉 <b>Вам начислено {coins} звезд ⭐ администратором!</b>")
                else:
                    send_telegram_message(chat_id, f"❌ Игрок {target_username} не найден")
                
                conn.close()
                return True
        except:
            send_telegram_message(chat_id, "❌ Ошибка формата: /add_coins username amount")
            return True
    
    elif text == "/admin_stats":
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT SUM(balance) FROM users')
        total_coins = cursor.fetchone()[0] or 0
        cursor.execute('SELECT SUM(total_deposited) FROM users')
        total_deposited = cursor.fetchone()[0] or 0
        cursor.execute('SELECT SUM(total_withdrawn) FROM users')
        total_withdrawn = cursor.fetchone()[0] or 0
        conn.close()
        
        stats_text = f"""
🔐 <b>АДМИН СТАТИСТИКА</b>

👥 Всего игроков: {total_users}
💰 Всего звезд в системе: {total_coins:,}
💵 Всего депозитов: {total_deposited:.2f} TON
💸 Всего выводов: {total_withdrawn:.2f} TON

⚡ <b>Команды:</b>
/add_coins username amount - Выдать звезды
"""
        send_telegram_message(chat_id, stats_text)
        return True
    
    return False

@app.route('/')
def home():
    return "🎰 PRO CASINO WITH REAL PAYMENTS 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            username = message["from"].get("username", "")
            first_name = message["from"].get("first_name", "Player")
            text = message.get("text", "")
            
            init_db()
            
            # Проверяем админские команды
            if handle_admin_command(user_id, username, text, chat_id):
                return jsonify({"status": "ok"})
            
            # Обычные команды
            if text == "/start":
                if not get_user(user_id): 
                    create_user(user_id, first_name)
                user = get_user(user_id)
                jackpot = get_jackpot()
                
                welcome_text = f"""
🎰 <b>PRO CASINO - РЕАЛЬНЫЕ ВЫВОДЫ</b> 🎰

✨ <b>Добро пожаловать, {first_name}!</b> ✨

💎 <b>ТВОЙ СТАТУС:</b>
⭐ Баланс: <b>{user['balance']:,} звезд</b>
👑 VIP: <b>{user['vip_level']}</b>
🏆 Побед: <b>{user['total_wins']}</b>

💰 <b>ДЖЕКПОТ:</b> <b>{jackpot:,} звезд!</b>

🚀 <b>ИГРЫ:</b>
🎯 /dice - Кости (1000 звезд)
🎪 /slots - Автоматы (500 звезд)
🎰 /jackpot - Супер джекпот (2000 звезд)

💳 <b>ФИНАНСЫ:</b>
💵 /deposit - Пополнить (TON)
💸 /withdraw - Вывести (TON)
💼 /balance - Профиль

🌟 1 TON = 1000 звезд
"""
                send_telegram_message(chat_id, welcome_text)
                
            elif text == "/deposit":
                deposit_text = f"""
💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>

🏦 <b>Отправьте TON на адрес:</b>
<code>{TON_WALLET}</code>

💎 <b>Курс:</b> 1 TON = 1000 звезд ⭐
💰 <b>Минимум:</b> 0.1 TON

📝 <b>В комментарии укажите:</b> @{username}

⚡ <b>После отправки напишите мне в ЛС</b> @{ADMIN_USERNAME}
"""
                send_telegram_message(chat_id, deposit_text)
                
            elif text == "/withdraw":
                user = get_user(user_id)
                if not user:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    return jsonify({"status": "ok"})
                
                withdraw_text = f"""
💸 <b>ВЫВОД СРЕДСТВ</b>

⭐ <b>Ваш баланс:</b> {user['balance']:,} звезд
💎 <b>Курс:</b> 1000 звезд = 1 TON
💰 <b>Минимум вывода:</b> 5000 звезд (5 TON)

📝 <b>Для вывода напишите мне:</b> @{ADMIN_USERNAME}

💬 <b>Укажите в сообщении:</b>
1. Сумму вывода (в звездах)
2. Ваш TON кошелек

⚡ <b>Выводы обрабатываются вручную!</b>
"""
                send_telegram_message(chat_id, withdraw_text)
                
            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    win_rate = (user['total_wins']/user['total_games']*100) if user['total_games'] > 0 else 0
                    balance_text = f"""
💼 <b>МОЙ ПРОФИЛЬ</b>

👤 <b>Игрок:</b> {user['username']}
👑 <b>VIP:</b> {user['vip_level']}
⭐ <b>Звезды:</b> {user['balance']:,}

📊 <b>Статистика:</b>
🎯 Побед: {user['total_wins']}
🎮 Игр: {user['total_games']}
📈 Win Rate: {win_rate:.1f}%

💳 <b>Финансы:</b>
💵 Депозиты: {user['total_deposited']:.2f} TON
💸 Выводы: {user['total_withdrawn']:.2f} TON
"""
                    send_telegram_message(chat_id, balance_text)
                else:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user['balance'] < 1000:
                    send_telegram_message(chat_id, f"❌ Нужно 1000 звезд! Баланс: {user['balance'] if user else 0}")
                    return jsonify({"status": "ok"})
                
                update_balance(user_id, -1000)
                user_dice = random.randint(1, 6)
                bot_dice = random.randint(1, 6)
                
                if random.random() < 0.05: user_dice = 777
                elif random.random() < 0.03: user_dice = 666
                
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅", 666: "😈", 777: "😇"}
                
                result_text = f"""
🎯 <b>КОСТИ</b>

🎲 <b>ТЫ:</b> {dice_emojis.get(user_dice, '🎲')} <b>{user_dice}</b>
🎲 <b>КАЗИНО:</b> {dice_emojis.get(bot_dice, '🎲')} <b>{bot_dice}</b>

"""
                
                if user_dice > bot_dice:
                    if user_dice == 777:
                        win_amount = 10000
                        result_text += f"😇 <b>АНГЕЛЬСКАЯ КОСТЬ! +{win_amount} звезд!</b>\n"
                    elif user_dice == 666:
                        win_amount = 6666
                        result_text += f"😈 <b>ДЕМОНИЧЕСКАЯ КОСТЬ! +{win_amount} звезд!</b>\n"
                    else:
                        win_amount = 2000
                        result_text += f"🎉 <b>ПОБЕДА! +{win_amount} звезд!</b>\n"
                    update_balance(user_id, win_amount)
                elif user_dice < bot_dice:
                    result_text += "😔 <b>Проигрыш</b>\n"
                else:
                    update_balance(user_id, 1000)
                    result_text += "🤝 <b>Ничья! Ставка возвращена</b>\n"
                
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if user_dice > bot_dice:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                user = get_user(user_id)
                result_text += f"\n⭐ <b>Баланс:</b> {user['balance']:,} звезд"
                
                send_telegram_message(chat_id, result_text)
            
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user['balance'] < 500:
                    send_telegram_message(chat_id, f"❌ Нужно 500 звезд! Баланс: {user['balance'] if user else 0}")
                    return jsonify({"status": "ok"})
                
                update_balance(user_id, -500)
                
                symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '⭐', '👑']
                slots = [random.choice(symbols) for _ in range(3)]
                
                slots_display = f"""
🎪 <b>АВТОМАТЫ</b>

┌───────────┐
│   {slots[0]} {slots[1]} {slots[2]}   │
└───────────┘
"""
                
                if slots[0] == slots[1] == slots[2]:
                    if slots[0] == '👑':
                        win_amount = 20000
                        result_text = f"{slots_display}\n🎊 <b>ДЖЕКПОТ! +{win_amount} звезд!</b> 💰"
                    elif slots[0] == '💎':
                        win_amount = 10000
                        result_text = f"{slots_display}\n💎 <b>АЛМАЗ! +{win_amount} звезд!</b> 💰"
                    else:
                        win_amount = 2000
                        result_text = f"{slots_display}\n🎉 <b>ВЫИГРЫШ! +{win_amount} звезд!</b> 💰"
                    update_balance(user_id, win_amount)
                
                elif slots[0] == slots[1] or slots[1] == slots[2]:
                    win_amount = 750
                    update_balance(user_id, win_amount)
                    result_text = f"{slots_display}\n🎉 <b>Выигрыш! +{win_amount} звезд!</b> 💰"
                
                else:
                    result_text = f"{slots_display}\n😔 <b>Повезет в следующий раз!</b>"
                
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if 'монет' in result_text:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                user = get_user(user_id)
                result_text += f"\n\n⭐ <b>Баланс:</b> {user['balance']:,} звезд"
                
                send_telegram_message(chat_id, result_text)
            
            elif text == "/jackpot":
                user = get_user(user_id)
                jackpot_amount = get_jackpot()
                
                if not user or user['balance'] < 2000:
                    send_telegram_message(chat_id, f"❌ Нужно 2000 звезд! Баланс: {user['balance'] if user else 0}")
                    return jsonify({"status": "ok"})
                
                update_balance(user_id, -2000)
                
                if random.random() < 0.02:
                    win_text = f"""
🎊 <b>ДЖЕКПОТ!</b>

💎 <b>ВЫ ВЫИГРАЛИ {jackpot_amount:,} ЗВЕЗД!</b>

🎉 <b>ПОЗДРАВЛЯЕМ!</b>
"""
                    update_balance(user_id, jackpot_amount)
                    update_jackpot(-jackpot_amount + 50000)
                    
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET jackpots = jackpots + 1, total_wins = total_wins + 1, total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                else:
                    win_text = f"""
😔 <b>Джекпот не выпал...</b>

💎 Джекпот растет: {jackpot_amount + 2000:,} звезд
"""
                    update_jackpot(2000)
                
                user = get_user(user_id)
                win_text += f"\n⭐ <b>Баланс:</b> {user['balance']:,} звезд"
                
                send_telegram_message(chat_id, win_text)
            
            else:
                send_telegram_message(chat_id, "❌ Неизвестная команда. Напиши /start")
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        return jsonify({"status": "error"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
