from flask import Flask, request, jsonify
import random
import sqlite3
import os
import time
from datetime import datetime, timedelta
import threading

app = Flask(__name__)
BOT_TOKEN = "8263606127:AAGK8Cvf2mbkTM2AMCg-Mc8NDjJrIE3bu_A"

# СЕКРЕТНЫЕ НАСТРОЙКИ
ADMIN_USERNAME = "nm0_0"
TON_WALLET = "UQDwad48c_DV0lPJ15gmgrSoFmwE_IAJrG-tc66trbdtj9tj"

class CasinoConfig:
    VIP_LEVELS = {
        1000: "🥉 БРОНЗА", 5000: "🥈 СЕРЕБРО", 10000: "🥇 ЗОЛОТО",
        50000: "💎 ДИАМАНТ", 100000: "👑 ЛЕГЕНДА", 500000: "🚀 МИЛЛИОНЕР"
    }
    JACKPOT_BASE = 50000
    DAILY_BONUS = [100, 500, 1000, 2000, 5000]

def init_db():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 5000,
            vip_level TEXT DEFAULT '👶 НОВИЧОК', total_wins INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0, jackpots INTEGER DEFAULT 0,
            total_deposited REAL DEFAULT 0, total_withdrawn REAL DEFAULT 0,
            registered_date TEXT, last_daily_bonus TEXT, referral_code TEXT UNIQUE,
            referred_by INTEGER, referral_bonus INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, experience INTEGER DEFAULT 0,
            last_login TEXT, is_vip BOOLEAN DEFAULT FALSE, vip_until TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT,
            amount REAL, currency TEXT, status TEXT, tx_hash TEXT, created_date TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS jackpot (amount INTEGER DEFAULT 50000)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    
    cursor.execute('INSERT OR IGNORE INTO jackpot (amount) VALUES (?)', (50000,))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                  ('double_deposit_active', 'false'))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                  ('free_spins_active', 'false'))
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
        'user_id': user[0], 'username': user[1], 'balance': user[2], 'vip_level': user[3],
        'total_wins': user[4], 'total_games': user[5], 'jackpots': user[6],
        'total_deposited': user[7], 'total_withdrawn': user[8], 'last_daily_bonus': user[10],
        'referral_code': user[11], 'level': user[14], 'last_login': user[16], 'is_vip': user[17]
    }

def create_user(user_id, username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    referral_code = f"REF{user_id}{random.randint(1000,9999)}"
    cursor.execute(
        'INSERT INTO users (user_id, username, balance, registered_date, referral_code, last_login) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, username, 5000, datetime.now().isoformat(), referral_code, datetime.now().isoformat())
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
    new_level = min(50, max(1, balance // 10000 + 1))
    cursor.execute('UPDATE users SET vip_level = ?, level = ? WHERE user_id = ?', (vip_level, new_level, user_id))
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

def get_setting(key):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def send_telegram_message(chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try: 
        requests.post(url, json=data, timeout=5)
    except: 
        pass

def handle_admin_command(user_id, username, text, chat_id):
    if username != ADMIN_USERNAME: return False
    
    if text.startswith("/add_coins "):
        try:
            parts = text.split()
            target_username, coins = parts[1], int(parts[2])
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
            target_user = cursor.fetchone()
            if target_user:
                update_balance(target_user[0], coins)
                send_telegram_message(chat_id, f"✅ Выдано {coins} звезд игроку {target_username}")
                send_telegram_message(target_user[0], f"🎉 Вам начислено {coins} звезд админом!")
            conn.close()
            return True
        except: pass
    
    elif text == "/admin_stats":
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT SUM(balance) FROM users')
        total_coins = cursor.fetchone()[0] or 0
        conn.close()
        send_telegram_message(chat_id, f"👥 Игроков: {total_users}\n💰 Звезд: {total_coins:,}")
        return True
    
    elif text.startswith("/global_message "):
        message = text.replace("/global_message ", "")
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        for user in users:
            send_telegram_message(user[0], f"📢 ОТ АДМИНА:\n{message}")
            time.sleep(0.1)
        conn.close()
        send_telegram_message(chat_id, "✅ Рассылка отправлена")
        return True
    
    elif text.startswith("/money_rain "):
        try:
            amount = int(text.split()[1])
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            for user in users:
                update_balance(user[0], amount)
                send_telegram_message(user[0], f"🌧️ Денежный дождь! +{amount} звезд!")
            conn.close()
            send_telegram_message(chat_id, f"✅ Дождь {amount} звезд для всех!")
            return True
        except: pass
    
    return False

def handle_star_payment(user_id, username, text, chat_id):
    if text.startswith("/pay "):
        try:
            parts = text.split()
            target_username, amount = parts[1], int(parts[2])
            user = get_user(user_id)
            if not user or user['balance'] < amount:
                send_telegram_message(chat_id, f"❌ Недостаточно звезд! Баланс: {user['balance'] if user else 0}")
                return True
            if amount < 100:
                send_telegram_message(chat_id, "❌ Минимум 100 звезд")
                return True
            
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
            target_user = cursor.fetchone()
            
            if target_user and target_user[0] != user_id:
                update_balance(user_id, -amount)
                update_balance(target_user[0], amount)
                commission = amount // 20
                admin_user = get_user_by_username(ADMIN_USERNAME)
                if admin_user: update_balance(admin_user['user_id'], commission)
                
                send_telegram_message(chat_id, f"✅ Перевод {amount} звезд игроку {target_username}")
                send_telegram_message(target_user[0], f"🎉 Вам перевели {amount} звезд от {username}")
            conn.close()
            return True
        except: pass
    return False

def get_user_by_username(username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if not user: return None
    return {'user_id': user[0], 'username': user[1], 'balance': user[2]}

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
            
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?', (datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
            
            if handle_admin_command(user_id, username, text, chat_id):
                return jsonify({"status": "ok"})
            
            if handle_star_payment(user_id, username, text, chat_id):
                return jsonify({"status": "ok"})
            
            if text == "/start":
                if not get_user(user_id): create_user(user_id, first_name)
                user = get_user(user_id)
                welcome_text = f"""
🎰 <b>PRO CASINO</b> 🎰

👋 <b>Добро пожаловать, {first_name}!</b>

⭐ Баланс: <b>{user['balance']:,} звезд</b>
👑 VIP: <b>{user['vip_level']}</b>
🎯 Уровень: <b>{user['level']}</b>

🎮 <b>Игры:</b>
🎯 /dice - Кости (1000⭐)
🎪 /slots - Автоматы (500⭐)  
🎰 /jackpot - Джекпот (2000⭐)

💫 <b>Бонусы:</b>
🎁 /daily - Ежедневный бонус
💸 /pay - Перевод звезд

💳 /deposit - Пополнить
💼 /balance - Профиль
"""
                send_telegram_message(chat_id, welcome_text)
                
            elif text == "/daily":
                user = get_user(user_id)
                if not user: return jsonify({"status": "ok"})
                today = datetime.now().date().isoformat()
                if user['last_daily_bonus'] == today:
                    send_telegram_message(chat_id, "❌ Уже получали бонус сегодня!")
                    return jsonify({"status": "ok"})
                bonus = random.choice(CasinoConfig.DAILY_BONUS)
                update_balance(user_id, bonus)
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET last_daily_bonus = ? WHERE user_id = ?', (today, user_id))
                conn.commit()
                conn.close()
                send_telegram_message(chat_id, f"🎁 Ежедневный бонус: {bonus} звезд!")
                
            elif text == "/pay":
                send_telegram_message(chat_id, "💸 <b>Перевод звезд:</b>\n<code>/pay username amount</code>\n\nПример: <code>/pay nm0_0 1000</code>")
                
            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    win_rate = (user['total_wins']/user['total_games']*100) if user['total_games'] > 0 else 0
                    balance_text = f"""
💼 <b>ПРОФИЛЬ</b>

👤 {user['username']}
👑 {user['vip_level']} 
⭐ {user['balance']:,} звезд
🎯 Уровень {user['level']}

📊 Статистика:
🎯 Побед: {user['total_wins']}
🎮 Игр: {user['total_games']}
📈 Win Rate: {win_rate:.1f}%
"""
                    send_telegram_message(chat_id, balance_text)
                    
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user['balance'] < 1000:
                    send_telegram_message(chat_id, "❌ Нужно 1000 звезд!")
                    return jsonify({"status": "ok"})
                update_balance(user_id, -1000)
                user_dice, bot_dice = random.randint(1,6), random.randint(1,6)
                if random.random() < 0.05: user_dice = 777
                result_text = f"🎯 <b>КОСТИ</b>\n\n🎲 Ты: {user_dice}\n🎲 Казино: {bot_dice}\n\n"
                if user_dice > bot_dice:
                    win = 10000 if user_dice == 777 else 2000
                    update_balance(user_id, win)
                    result_text += f"🎉 ПОБЕДА! +{win} звезд!"
                elif user_dice < bot_dice:
                    result_text += "😔 Проигрыш"
                else:
                    update_balance(user_id, 1000)
                    result_text += "🤝 Ничья!"
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if user_dice > bot_dice:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                send_telegram_message(chat_id, result_text)
                
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user['balance'] < 500:
                    send_telegram_message(chat_id, "❌ Нужно 500 звезд!")
                    return jsonify({"status": "ok"})
                update_balance(user_id, -500)
                symbols = ['🍒','🍋','🍊','🍇','🔔','💎','⭐','👑']
                slots = [random.choice(symbols) for _ in range(3)]
                result_text = f"🎪 <b>АВТОМАТЫ</b>\n\n┌───┐\n│ {' '.join(slots)} │\n└───┘\n\n"
                if slots[0] == slots[1] == slots[2]:
                    win = 20000 if slots[0] == '👑' else 10000 if slots[0] == '💎' else 2000
                    update_balance(user_id, win)
                    result_text += f"🎊 ДЖЕКПОТ! +{win} звезд!"
                elif slots[0] == slots[1] or slots[1] == slots[2]:
                    update_balance(user_id, 750)
                    result_text += "🎉 Выигрыш! +750 звезд!"
                else:
                    result_text += "😔 Повезет в следующий раз!"
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if 'звезд' in result_text:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                send_telegram_message(chat_id, result_text)
                
            elif text == "/jackpot":
                user = get_user(user_id)
                jackpot = get_jackpot()
                if not user or user['balance'] < 2000:
                    send_telegram_message(chat_id, "❌ Нужно 2000 звезд!")
                    return jsonify({"status": "ok"})
                update_balance(user_id, -2000)
                if random.random() < 0.02:
                    update_balance(user_id, jackpot)
                    update_jackpot(-jackpot + 50000)
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET jackpots = jackpots + 1, total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                    send_telegram_message(chat_id, f"🎊 <b>ДЖЕКПОТ!</b>\n\n💎 ВЫ ВЫИГРАЛИ {jackpot:,} ЗВЕЗД! 🎉")
                else:
                    update_jackpot(2000)
                    send_telegram_message(chat_id, f"😔 Джекпот не выпал...\n💎 Теперь: {jackpot+2000:,} звезд")
                    
            else:
                send_telegram_message(chat_id, "❌ Неизвестная команда. Напиши /start")
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        return jsonify({"status": "error"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
