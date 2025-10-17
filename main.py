from flask import Flask, request, jsonify
import random
import sqlite3
import os
import time
from datetime import datetime, timedelta
import threading

app = Flask(__name__)
BOT_TOKEN = "8263606127:AAGK8Cvf2mbkTM2AMCg-Mc8NDjJrIE3bu_A"

ADMIN_USERNAME = "nm0_0"
TON_WALLET = "UQDwad48c_DV0lPJ15gmgrSoFmwE_IAJrG-tc66trbdtj9tj"

class CasinoConfig:
    VIP_LEVELS = {
        1000: "🥉 БРОНЗА", 5000: "🥈 СЕРЕБРО", 10000: "🥇 ЗОЛОТО",
        50000: "💎 ДИАМАНТ", 100000: "👑 ЛЕГЕНДА", 500000: "🚀 МИЛЛИОНЕР",
        1000000: "🌟 БОГ КАЗИНО"
    }
    JACKPOT_BASE = 50000
    DAILY_BONUS = [100, 500, 1000, 2000, 5000]

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
            registered_date TEXT, 
            last_daily_bonus TEXT, 
            referral_code TEXT UNIQUE,
            referred_by INTEGER, 
            referral_bonus INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, 
            experience INTEGER DEFAULT 0,
            last_login TEXT, 
            is_vip BOOLEAN DEFAULT FALSE, 
            vip_until TEXT,
            hidden_balance INTEGER DEFAULT 0
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
    cursor.execute('CREATE TABLE IF NOT EXISTS jackpot (amount INTEGER DEFAULT 50000)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS admin_secrets (key TEXT PRIMARY KEY, value TEXT)')
    
    cursor.execute('INSERT OR IGNORE INTO jackpot (amount) VALUES (?)', (50000,))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', 
                  ('double_deposit_active', 'false'))
    cursor.execute('INSERT OR IGNORE INTO admin_secrets (key, value) VALUES (?, ?)', 
                  ('god_mode', 'false'))
    cursor.execute('INSERT OR IGNORE INTO admin_secrets (key, value) VALUES (?, ?)', 
                  ('invisible_mode', 'false'))
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
        'referral_code': user[11], 'level': user[14], 'last_login': user[16], 'is_vip': user[17],
        'hidden_balance': user[19]
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

def update_hidden_balance(user_id, amount):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET hidden_balance = hidden_balance + ? WHERE user_id = ?', (amount, user_id))
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

def get_secret(key):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM admin_secrets WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_secret(key, value):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO admin_secrets (key, value) VALUES (?, ?)', (key, value))
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

def send_dice_animation(chat_id):
    animations = ["🎲 Бросаем кости...", "🎲 Кости летят...", "🎲 Почти видим...", "🎲 Результат..."]
    for anim in animations:
        send_telegram_message(chat_id, anim)
        time.sleep(0.8)

def send_slots_animation(chat_id):
    symbols = ['🍒','🍋','🍊','🍇','🔔','💎','⭐','👑']
    for i in range(5):
        spinning = [random.choice(symbols) for _ in range(3)]
        send_telegram_message(chat_id, f"🎪 Крутим...\n┌───┐\n│ {' '.join(spinning)} │\n└───┘")
        time.sleep(0.5)

def send_jackpot_animation(chat_id):
    animations = ["💰 Джекпот крутится...", "💰 Сумма растет...", "💰 Почти угадали...", "💰 СЕКУНДОЧКУ...", "💰 РЕЗУЛЬТАТ..."]
    for anim in animations:
        send_telegram_message(chat_id, anim)
        time.sleep(1)

def send_roulette_animation(chat_id):
    numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    for i in range(6):
        spinning = [random.choice(numbers) for _ in range(3)]
        send_telegram_message(chat_id, f"🎡 Крутим рулетку...\n┌─────┐\n│ {' '.join(spinning)} │\n└─────┘")
        time.sleep(0.6)

def handle_admin_command(user_id, username, text, chat_id):
    if username != ADMIN_USERNAME: 
        return False
    
    # ФИКС: Команда добавления звезд
    if text.startswith("/add_coins "):
        try:
            parts = text.split()
            if len(parts) >= 3:
                target_username = parts[1]
                coins = int(parts[2])
                
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
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Ошибка: {str(e)}")
            return True
    
    # ФИКС: Статистика админа
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
        cursor.execute('SELECT SUM(hidden_balance) FROM users')
        total_hidden = cursor.fetchone()[0] or 0
        conn.close()
        
        stats_text = f"""
🔐 <b>СУПЕР АДМИН СТАТИСТИКА</b>

👥 Всего игроков: {total_users}
💰 Всего звезд в системе: {total_coins:,}
🕶️ Секретных звезд: {total_hidden:,}
💵 Всего депозитов: {total_deposited:.2f} TON
💸 Всего выводов: {total_withdrawn:.2f} TON
🎰 Джекпот: {get_jackpot():,} звезд

⚡ <b>СЕКРЕТНЫЕ КОМАНДЫ:</b>
/god_mode on/off - Режим бога
/invisible on/off - Невидимка
/stealth_coins user amount - Секретная выдача
/hidden_balance - Мой секретный баланс
/secret_rain amount - Секретный дождь
/system_wipe - 💀 ОПАСНО! Сброс всей системы
"""
        send_telegram_message(chat_id, stats_text)
        return True
    
    # ФИКС: Топ игроков
    elif text == "/top_players":
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username, balance, vip_level FROM users ORDER BY balance DESC LIMIT 10')
        top_players = cursor.fetchall()
        conn.close()
        
        top_text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
        for i, (username, balance, vip) in enumerate(top_players, 1):
            top_text += f"{i}. {username} - {balance:,} ⭐ {vip}\n"
        
        send_telegram_message(chat_id, top_text)
        return True
    
    # ФИКС: Глобальная рассылка
    elif text.startswith("/global_message "):
        message = text.replace("/global_message ", "")
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        conn.close()
        
        sent = 0
        for user in users:
            if send_telegram_message(user[0], f"📢 <b>ОТ АДМИНИСТРАЦИИ:</b>\n\n{message}"):
                sent += 1
            time.sleep(0.1)
        
        send_telegram_message(chat_id, f"✅ Рассылка отправлена {sent} пользователям")
        return True
    
    # ФИКС: Денежный дождь
    elif text.startswith("/money_rain "):
        try:
            amount = int(text.split()[1])
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            
            for user in users:
                update_balance(user[0], amount)
                send_telegram_message(user[0], f"🌧️ <b>ДЕНЕЖНЫЙ ДОЖДЬ!</b>\n\n+{amount} звезд от администрации! 💰")
            
            conn.close()
            send_telegram_message(chat_id, f"✅ Денежный дождь {amount} звезд для всех игроков!")
            return True
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Ошибка: {str(e)}")
            return True
    
    # Секретные команды
    elif text.startswith("/god_mode "):
        state = text.split()[1].lower()
        if state in ['on', 'off']:
            set_secret('god_mode', 'true' if state == 'on' else 'false')
            status = "ВКЛЮЧЕН" if state == 'on' else "ВЫКЛЮЧЕН"
            send_telegram_message(chat_id, f"👑 <b>РЕЖИМ БОГА {status}!</b>")
            return True
    
    elif text.startswith("/invisible "):
        state = text.split()[1].lower()
        if state in ['on', 'off']:
            set_secret('invisible_mode', 'true' if state == 'on' else 'false')
            status = "ВКЛЮЧЕН" if state == 'on' else "ВЫКЛЮЧЕН"
            send_telegram_message(chat_id, f"👻 <b>РЕЖИМ НЕВИДИМКИ {status}!</b>")
            return True
    
    elif text.startswith("/stealth_coins "):
        try:
            parts = text.split()
            target_username, coins = parts[1], int(parts[2])
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (target_username,))
            target_user = cursor.fetchone()
            
            if target_user:
                update_hidden_balance(target_user[0], coins)
                send_telegram_message(chat_id, f"🕶️ <b>СЕКРЕТНО:</b> {coins} звезд игроку {target_username}")
            conn.close()
            return True
        except: 
            return False
    
    elif text == "/hidden_balance":
        user = get_user(user_id)
        if user:
            send_telegram_message(chat_id, f"🕶️ <b>СЕКРЕТНЫЙ БАЛАНС:</b> {user['hidden_balance']:,} звезд")
        return True
    
    elif text.startswith("/secret_rain "):
        try:
            amount = int(text.split()[1])
            conn = sqlite3.connect('casino.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            for user in users:
                update_hidden_balance(user[0], amount)
            conn.close()
            send_telegram_message(chat_id, f"🕶️ <b>СЕКРЕТНЫЙ ДОЖДЬ:</b> {amount} звезд для всех!")
            return True
        except: 
            return False
    
    elif text == "/system_wipe":
        send_telegram_message(chat_id, "💀 <b>ОПАСНАЯ КОМАНДА!</b>\n\nДля подтверждения введи: /confirm_wipe")
        return True
    
    elif text == "/confirm_wipe":
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users')
        cursor.execute('DELETE FROM transactions')
        cursor.execute('UPDATE jackpot SET amount = 50000')
        conn.commit()
        conn.close()
        send_telegram_message(chat_id, "💀 <b>СИСТЕМА ПОЛНОСТЬЮ СБРОШЕНА!</b>")
        return True
    
    return False

def handle_star_payment(user_id, username, text, chat_id):
    if text.startswith("/pay "):
        try:
            parts = text.split()
            if len(parts) >= 3:
                target_username = parts[1]
                amount = int(parts[2])
                
                user = get_user(user_id)
                if not user or user['balance'] < amount:
                    send_telegram_message(chat_id, f"❌ Недостаточно звезд! Баланс: {user['balance'] if user else 0}")
                    return True
                
                if amount < 100:
                    send_telegram_message(chat_id, "❌ Минимальная сумма перевода: 100 звезд")
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
                    if admin_user:
                        update_balance(admin_user['user_id'], commission)
                    
                    send_telegram_message(chat_id, f"✅ <b>Перевод выполнен!</b>\n\n👤 Получатель: {target_username}\n💫 Сумма: {amount} звезд\n📊 Комиссия: {commission} звезд\n\n⭐ Новый баланс: {user['balance'] - amount}")
                    send_telegram_message(target_user[0], f"🎉 <b>Вам перевели {amount} звезд!</b>\n\n👤 От: {username}\n💫 Сумма: {amount} звезд")
                    
                elif target_user and target_user[0] == user_id:
                    send_telegram_message(chat_id, "❌ Нельзя переводить себе!")
                else:
                    send_telegram_message(chat_id, f"❌ Игрок {target_username} не найден")
                
                conn.close()
                return True
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Ошибка перевода: {str(e)}")
            return True
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
🎯 Уровень: <b>{user['level']}</b>

💰 <b>ДЖЕКПОТ:</b> <b>{jackpot:,} звезд!</b>

🚀 <b>ИГРЫ:</b>
🎯 /dice - Кости (1000 звезд)
🎪 /slots - Автоматы (500 звезд)
🎰 /jackpot - Супер джекпот (2000 звезд)
🎡 /roulette - Рулетка (1500 звезд)

💫 <b>БОНУСЫ:</b>
🎁 /daily - Ежедневный бонус
👥 /referral - Реферальная система
💸 /pay - Перевести звезды
📊 /stats - Статистика игроков

💳 <b>ФИНАНСЫ:</b>
💵 /deposit - Пополнить (TON)
💸 /withdraw - Вывести (TON)
💼 /balance - Профиль
📈 /analytics - Финансовая аналитика

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

📝 <b>В комментарии укажите ваш username:</b> @{username}

⚡ <b>После отправки напишите мне:</b> @{ADMIN_USERNAME}

🔄 <b>Баланс пополнится в течение 5 минут!</b>
"""
                send_telegram_message(chat_id, deposit_text)
                
            elif text == "/withdraw":
                user = get_user(user_id)
                if not user:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    return jsonify({"status": "ok"})
                
                if user['balance'] < 5000:
                    send_telegram_message(chat_id, f"❌ Минимум для вывода 5000 звезд! Ваш баланс: {user['balance']:,}")
                    return jsonify({"status": "ok"})
                
                withdraw_text = f"""
💸 <b>ВЫВОД СРЕДСТВ</b>

⭐ <b>Ваш баланс:</b> {user['balance']:,} звезд
💎 <b>Курс:</b> 1000 звезд = 1 TON
💰 <b>Минимум вывода:</b> 5000 звезд (5 TON)

📝 <b>Для вывода напишите:</b> @{ADMIN_USERNAME}

💬 <b>Укажите в сообщении:</b>
1. Сумму вывода (в звездах)
2. Ваш TON кошелек

⚡ <b>Выводы обрабатываются вручную в течение 24 часов!</b>
"""
                send_telegram_message(chat_id, withdraw_text)
                
            elif text == "/daily":
                user = get_user(user_id)
                if not user:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    return jsonify({"status": "ok"})
                
                today = datetime.now().date().isoformat()
                if user['last_daily_bonus'] == today:
                    send_telegram_message(chat_id, "❌ Сегодняшний бонус уже получен!")
                    return jsonify({"status": "ok"})
                
                bonus = random.choice(CasinoConfig.DAILY_BONUS)
                update_balance(user_id, bonus)
                
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET last_daily_bonus = ? WHERE user_id = ?', (today, user_id))
                conn.commit()
                conn.close()
                
                daily_text = f"""
🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС</b>

💰 <b>Вы получили: {bonus} звезд!</b>

💫 Заходите завтра за новым бонусом!
⭐ Баланс: {user['balance'] + bonus:,} звезд
"""
                send_telegram_message(chat_id, daily_text)
                
            elif text == "/pay":
                pay_text = f"""
💫 <b>ПЕРЕВОД ЗВЕЗД</b>

📤 <b>Переведите звезды другому игроку:</b>

💎 <b>Формат:</b>
<code>/pay username amount</code>

🎯 <b>Пример:</b>
<code>/pay {ADMIN_USERNAME} 1000</code>

📊 <b>Комиссия:</b> 5%
💰 <b>Минимум:</b> 100 звезд

⚡ <b>Быстро и безопасно!</b>
"""
                send_telegram_message(chat_id, pay_text)

            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    win_rate = (user['total_wins']/user['total_games']*100) if user['total_games'] > 0 else 0
                    balance_text = f"""
💼 <b>МОЙ ПРОФИЛЬ</b>

👤 <b>Игрок:</b> {user['username']}
👑 <b>VIP:</b> {user['vip_level']}
⭐ <b>Звезды:</b> {user['balance']:,}
🎯 <b>Уровень:</b> {user['level']}

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

            elif text == "/stats":
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 5')
                top_players = cursor.fetchall()
                conn.close()
                
                stats_text = f"""
📊 <b>СТАТИСТИКА КАЗИНО</b>

👥 Всего игроков: {total_users}
💰 Джекпот: {get_jackpot():,} звезд

🏆 <b>ТОП-5 ИГРОКОВ:</b>
"""
                for i, (username, balance) in enumerate(top_players, 1):
                    stats_text += f"{i}. {username} - {balance:,} ⭐\n"
                
                stats_text += "\n🎰 <b>Игры доступны:</b>\n/dice /slots /jackpot /roulette"
                send_telegram_message(chat_id, stats_text)

            elif text == "/analytics":
                user = get_user(user_id)
                if not user:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    return jsonify({"status": "ok"})
                
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
                
                analytics_text = f"""
📈 <b>ФИНАНСОВАЯ АНАЛИТИКА</b>

👥 <b>Общая статистика:</b>
• Всего игроков: {total_users}
• Звезд в системе: {total_coins:,}
• Общие депозиты: {total_deposited:.2f} TON
• Общие выводы: {total_withdrawn:.2f} TON

💼 <b>Ваша статистика:</b>
• Ваш баланс: {user['balance']:,} звезд
• Ваши депозиты: {user['total_deposited']:.2f} TON
• Ваши выводы: {user['total_withdrawn']:.2f} TON
• Win Rate: {(user['total_wins']/user['total_games']*100) if user['total_games'] > 0 else 0:.1f}%

💰 <b>Экономика:</b>
• 1 TON = 1000 звезд
• Джекпот: {get_jackpot():,} звезд
"""
                send_telegram_message(chat_id, analytics_text)
                
            elif text == "/roulette":
                user = get_user(user_id)
                if not user or user['balance'] < 1500:
                    send_telegram_message(chat_id, "❌ Нужно 1500 звезд для игры в рулетку!")
                    return jsonify({"status": "ok"})
                
                send_roulette_animation(chat_id)
                update_balance(user_id, -1500)
                
                # Рулетка с числами 0-9
                winning_number = random.randint(0, 9)
                user_bet = random.randint(0, 9)  # В будущем можно добавить выбор числа
                
                result_text = f"""
🎡 <b>РУЛЕТКА</b>

🎯 Ваше число: {user_bet}️⃣
🎯 Выпавшее число: {winning_number}️⃣

"""
                
                if user_bet == winning_number:
                    win = 10000
                    update_balance(user_id, win)
                    result_text += f"🎊 <b>ДЖЕКПОТ! УГАДАЛИ ЧИСЛО! +{win} звезд!</b>"
                elif abs(user_bet - winning_number) <= 1:
                    win = 3000
                    update_balance(user_id, win)
                    result_text += f"🎉 <b>Близко! +{win} звезд!</b>"
                else:
                    result_text += "😔 <b>Не угадали</b>"
                
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if user_bet == winning_number or abs(user_bet - winning_number) <= 1:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                user = get_user(user_id)
                result_text += f"\n\n⭐ Баланс: {user['balance']:,} звезд"
                send_telegram_message(chat_id, result_text)
                
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user['balance'] < 1000:
                    send_telegram_message(chat_id, "❌ Нужно 1000 звезд!")
                    return jsonify({"status": "ok"})
                
                send_dice_animation(chat_id)
                update_balance(user_id, -1000)
                
                user_dice, bot_dice = random.randint(1,6), random.randint(1,6)
                if random.random() < 0.05: user_dice = 777
                elif random.random() < 0.03: user_dice = 666
                
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅", 666: "😈", 777: "😇"}
                
                result_text = f"🎯 <b>КОСТИ</b>\n\n🎲 Ты: {dice_emojis.get(user_dice, '🎲')} <b>{user_dice}</b>\n🎲 Казино: {dice_emojis.get(bot_dice, '🎲')} <b>{bot_dice}</b>\n\n"
                
                if user_dice > bot_dice:
                    if user_dice == 777:
                        win = 10000
                        result_text += f"😇 <b>АНГЕЛЬСКАЯ КОСТЬ! +{win} звезд!</b>"
                    elif user_dice == 666:
                        win = 6666  
                        result_text += f"😈 <b>ДЕМОНИЧЕСКАЯ КОСТЬ! +{win} звезд!</b>"
                    else:
                        win = 2000
                        result_text += f"🎉 <b>ПОБЕДА! +{win} звезд!</b>"
                    update_balance(user_id, win)
                elif user_dice < bot_dice:
                    result_text += "😔 <b>Проигрыш</b>"
                else:
                    update_balance(user_id, 1000)
                    result_text += "🤝 <b>Ничья! Ставка возвращена</b>"
                    
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if user_dice > bot_dice:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                user = get_user(user_id)
                result_text += f"\n\n⭐ Баланс: {user['balance']:,} звезд"
                send_telegram_message(chat_id, result_text)
                
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user['balance'] < 500:
                    send_telegram_message(chat_id, "❌ Нужно 500 звезд!")
                    return jsonify({"status": "ok"})
                
                send_slots_animation(chat_id)
                update_balance(user_id, -500)
                
                symbols = ['🍒','🍋','🍊','🍇','🔔','💎','⭐','👑']
                slots = [random.choice(symbols) for _ in range(3)]
                
                result_text = f"🎪 <b>АВТОМАТЫ</b>\n\n┌───┐\n│ {' '.join(slots)} │\n└───┘\n\n"
                
                if slots[0] == slots[1] == slots[2]:
                    if slots[0] == '👑':
                        win = 20000
                        result_text += f"🎊 <b>ДЖЕКПОТ! +{win} звезд!</b> 💰"
                    elif slots[0] == '💎':
                        win = 10000
                        result_text += f"💎 <b>АЛМАЗ! +{win} звезд!</b> 💰"
                    else:
                        win = 2000
                        result_text += f"🎉 <b>ВЫИГРЫШ! +{win} звезд!</b> 💰"
                    update_balance(user_id, win)
                elif slots[0] == slots[1] or slots[1] == slots[2]:
                    win = 750
                    update_balance(user_id, win)
                    result_text += f"🎉 <b>Выигрыш! +{win} звезд!</b> 💰"
                else:
                    result_text += "😔 <b>Повезет в следующий раз!</b>"
                    
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                if 'звезд' in result_text:
                    cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                user = get_user(user_id)
                result_text += f"\n\n⭐ Баланс: {user['balance']:,} звезд"
                send_telegram_message(chat_id, result_text)
                
            elif text == "/jackpot":
                user = get_user(user_id)
                jackpot = get_jackpot()
                if not user or user['balance'] < 2000:
                    send_telegram_message(chat_id, "❌ Нужно 2000 звезд!")
                    return jsonify({"status": "ok"})
                
                send_jackpot_animation(chat_id)
                update_balance(user_id, -2000)
                
                if random.random() < 0.02:
                    update_balance(user_id, jackpot)
                    update_jackpot(-jackpot + 50000)
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET jackpots = jackpots + 1, total_wins = total_wins + 1, total_games = total_games + 1 WHERE user_id = ?', (user_id,))
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
