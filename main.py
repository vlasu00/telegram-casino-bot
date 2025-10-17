from flask import Flask, request, jsonify
import random
import sqlite3
import os
import logging
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8263606127:AAGK8Cvf2mbkTM2AMCg-Mc8NDjJrIE3bu_A"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

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
            registered_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        return None
    return {
        'user_id': user[0],
        'username': user[1],
        'balance': user[2],
        'vip_level': user[3],
        'total_wins': user[4],
        'total_games': user[5]
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
    
    # Обновляем VIP статус
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    balance = cursor.fetchone()[0]
    
    vip_level = "👶 НОВИЧОК"
    if balance >= 100000:
        vip_level = "👑 ЛЕГЕНДА"
    elif balance >= 50000:
        vip_level = "💎 ДИАМАНТ"
    elif balance >= 10000:
        vip_level = "🥇 ЗОЛОТО"
    elif balance >= 5000:
        vip_level = "🥈 СЕРЕБРО"
    
    cursor.execute('UPDATE users SET vip_level = ? WHERE user_id = ?', (vip_level, user_id))
    conn.commit()
    conn.close()

def send_telegram_message(chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

@app.route('/')
def home():
    return "🎰 ULTRA CASINO BOT is RUNNING! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            username = message["from"].get("first_name", "Player")
            text = message.get("text", "")
            
            # Инициализация БД
            init_db()
            
            # Обработка команд
            if text == "/start":
                if not get_user(user_id):
                    create_user(user_id, username)
                user = get_user(user_id)
                
                welcome_text = f"""
🎰 <b>ULTRA CASINO VIP</b> 🎰

✨ <b>Добро пожаловать, {username}!</b> ✨

💎 <b>Твой статус:</b>
💰 Баланс: <b>{user['balance']:,} монет</b>
👑 VIP: <b>{user['vip_level']}</b>
🏆 Побед: <b>{user['total_wins']}</b>
🎮 Игр: <b>{user['total_games']}</b>

🚀 <b>Доступные игры:</b>
🎯 /dice - Кости (500 монет)
🎪 /slots - Автоматы (200 монет)
🎲 /roulette - Рулетка (1000 монет)

💼 <b>Команды:</b>
💼 /balance - Баланс
🎁 /daily - Бонус
👑 /top - Топ игроков

🌟 <b>Удачи в игре!</b> 🍀
"""
                send_telegram_message(chat_id, welcome_text)
                
            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    win_rate = (user['total_wins'] / user['total_games'] * 100) if user['total_games'] > 0 else 0
                    balance_text = f"""
💼 <b>МОЙ ПРОФИЛЬ</b>

👤 <b>Игрок:</b> {user['username']}
👑 <b>VIP Статус:</b> {user['vip_level']}
💰 <b>Баланс:</b> {user['balance']:,} монет

📊 <b>Статистика:</b>
🎯 Побед: {user['total_wins']}
🎮 Всего игр: {user['total_games']}
📈 Процент побед: {win_rate:.1f}%

✨ <b>Продолжайте в том же духе!</b>
"""
                    send_telegram_message(chat_id, balance_text)
                else:
                    send_telegram_message(chat_id, "❌ Напиши /start чтобы начать!")
                    
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user['balance'] < 500:
                    send_telegram_message(chat_id, "❌ Недостаточно средств! Нужно 500 монет")
                else:
                    update_balance(user_id, -500)
                    user_dice = random.randint(1, 6)
                    bot_dice = random.randint(1, 6)
                    
                    # Спец-кости для вау-эффекта
                    if random.random() < 0.05:  # 5% шанс на золотую кость
                        user_dice = 7
                    
                    dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅", 7: "💰"}
                    
                    result_text = f"""
🎯 <b>ИГРА В КОСТИ</b> 🎯

🎲 <b>ТВОЯ КОСТЬ:</b> {dice_emojis[user_dice]} <b>{user_dice}</b>
🎲 <b>КОСТЬ КАЗИНО:</b> {dice_emojis[bot_dice]} <b>{bot_dice}</b>

"""
                    
                    if user_dice > bot_dice:
                        if user_dice == 7:
                            win_amount = 5000
                            result_text += f"🎊 <b>ЗОЛОТАЯ КОСТЬ! МЕГА ВЫИГРЫШ!</b> 🎊\n"
                        else:
                            win_amount = 1000
                        result_text += f"🎉 <b>ПОБЕДА! +{win_amount} монет!</b>\n"
                        update_balance(user_id, win_amount)
                    elif user_dice < bot_dice:
                        result_text += "😔 <b>Проигрыш</b>\n"
                    else:
                        update_balance(user_id, 500)
                        result_text += "🤝 <b>Ничья! Ставка возвращена</b>\n"
                    
                    # Обновляем статистику
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                    if user_dice > bot_dice:
                        cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                    
                    user = get_user(user_id)
                    result_text += f"\n💰 <b>Твой баланс:</b> {user['balance']:,} монет"
                    
                    send_telegram_message(chat_id, result_text)
            
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user['balance'] < 200:
                    send_telegram_message(chat_id, "❌ Недостаточно средств! Нужно 200 монет")
                else:
                    update_balance(user_id, -200)
                    
                    symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '⭐', '🔥', '👑']
                    weights = [20, 18, 16, 14, 10, 8, 6, 5, 3]
                    slots = [random.choices(symbols, weights=weights)[0] for _ in range(3)]
                    
                    slots_display = f"""
🎪 <b>ИГРОВЫЕ АВТОМАТЫ</b> 🎪

┌───────────┐
│   {slots[0]} {slots[1]} {slots[2]}   │
└───────────┘
"""
                    
                    if slots[0] == slots[1] == slots[2]:
                        if slots[0] == '👑':
                            win_amount = 10000
                            result_text = f"{slots_display}\n🎊 <b>КОРОЛЕВСКИЙ ДЖЕКПОТ! 👑</b> 🎊\n+{win_amount} монет! 💰"
                        elif slots[0] == '💎':
                            win_amount = 5000
                            result_text = f"{slots_display}\n💎 <b>АЛМАЗНЫЙ ВЫИГРЫШ!</b> 💎\n+{win_amount} монет! 💰"
                        else:
                            win_amount = 1000
                            result_text = f"{slots_display}\n🎉 <b>БОЛЬШОЙ ВЫИГРЫШ!</b> 🎉\n+{win_amount} монет! 💰"
                        update_balance(user_id, win_amount)
                    
                    elif slots[0] == slots[1] or slots[1] == slots[2]:
                        win_amount = 400
                        update_balance(user_id, win_amount)
                        result_text = f"{slots_display}\n🎉 <b>Выигрыш!</b> Два одинаковых символа!\n+{win_amount} монет! 💰"
                    
                    else:
                        result_text = f"{slots_display}\n😔 <b>Повезет в следующий раз!</b>"
                    
                    # Обновляем статистику
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                    if 'монет' in result_text:
                        cursor.execute('UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                    
                    user = get_user(user_id)
                    result_text += f"\n\n💰 <b>Твой баланс:</b> {user['balance']:,} монет"
                    
                    send_telegram_message(chat_id, result_text)
            
            elif text == "/roulette":
                send_telegram_message(chat_id, "🎲 <b>Рулетка скоро будет доступна!</b>\n\nА пока поиграй в 🎯 /dice или 🎪 /slots!")
            
            elif text == "/daily":
                send_telegram_message(chat_id, "🎁 <b>Ежедневные бонусы скоро!</b>\n\nИграй в игры чтобы увеличить баланс! 🎰")
            
            elif text == "/top":
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('SELECT username, balance, vip_level FROM users ORDER BY balance DESC LIMIT 10')
                top_users = cursor.fetchall()
                conn.close()
                
                top_text = "👑 <b>ТОП-10 ИГРОКОВ</b> 👑\n\n"
                
                for i, (username, balance, vip_level) in enumerate(top_users, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    top_text += f"{medal} <b>{username}</b>\n   💰 {balance:,} монет | {vip_level}\n"
                
                send_telegram_message(chat_id, top_text)
            
            else:
                send_telegram_message(chat_id, "❌ Неизвестная команда. Напиши /start для начала")
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
