from flask import Flask, request, jsonify
import random
import sqlite3
import os
import time
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = "8263606127:AAGK8Cvf2mbkTM2AMCg-Mc8NDjJrIE3bu_A"

# ВАУ КОНФИГ
class WowConfig:
    VIP_LEVELS = {
        1000: "🥉 БРОНЗА",
        5000: "🥈 СЕРЕБРО", 
        10000: "🥇 ЗОЛОТО",
        50000: "💎 ДИАМАНТ",
        100000: "👑 ЛЕГЕНДА"
    }
    JACKPOT_BASE = 25000

def init_db():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 10000,
            vip_level TEXT DEFAULT '👶 НОВИЧОК',
            total_wins INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            jackpots INTEGER DEFAULT 0,
            registered_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jackpot (
            amount INTEGER DEFAULT 25000
        )
    ''')
    cursor.execute('SELECT * FROM jackpot')
    if not cursor.fetchone():
        cursor.execute('INSERT INTO jackpot (amount) VALUES (?)', (25000,))
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
        'jackpots': user[6]
    }

def create_user(user_id, username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (user_id, username, balance, registered_date) VALUES (?, ?, ?, ?)',
        (user_id, username, 10000, datetime.now().isoformat())
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
    for threshold, level in WowConfig.VIP_LEVELS.items():
        if balance >= threshold: vip_level = level
    cursor.execute('UPDATE users SET vip_level = ? WHERE user_id = ?', (vip_level, user_id))
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

# ВАУ АНИМАЦИИ
class WowAnimations:
    @staticmethod
    def firework(): return "🎇🎆✨🌟💫⭐🔥💥"
    @staticmethod
    def coins(): return "💰💵💴💶💷💎💍💸"
    @staticmethod
    def slots_roll(): return "🎰 → 🎰 → 🎰 → 💎"

@app.route('/')
def home():
    return "🎰 MEGA WOW CASINO 🚀"

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
            
            init_db()
            
            if text == "/start":
                if not get_user(user_id): create_user(user_id, username)
                user = get_user(user_id)
                jackpot = get_jackpot()
                
                welcome_text = f"""
{WowAnimations.firework()}

🎰 <b>MEGA WOW CASINO</b> 🎰

{WowAnimations.coins()}

✨ <b>ДОБРО ПОЖАЛОВАТЬ, {username.upper()}!</b> ✨

💎 <b>ТВОЙ СТАТУС:</b>
💰 Баланс: <b>{user['balance']:,} монет</b>
👑 VIP: <b>{user['vip_level']}</b>
🏆 Побед: <b>{user['total_wins']}</b>
🎮 Игр: <b>{user['total_games']}</b>
🎊 Джекпотов: <b>{user['jackpots']}</b>

{WowAnimations.firework()}

💎 <b>СУПЕР ДЖЕКПОТ:</b> <b>{jackpot:,} МОНЕТ!</b>

{WowAnimations.coins()}

🚀 <b>КОМАНДЫ:</b>
🎯 /dice - Кости (1000 монет)
🎪 /slots - Автоматы (500 монет)  
🎰 /jackpot - Выиграй джекпот! (2000 монет)
💼 /balance - Профиль
👑 /top - Топ легенд

🌟 <b>УДАЧИ!</b> 🍀
"""
                send_telegram_message(chat_id, welcome_text)
                
            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    win_rate = (user['total_wins']/user['total_games']*100) if user['total_games'] > 0 else 0
                    balance_text = f"""
💎 <b>МОЙ ПРОФИЛЬ</b> 💎

{WowAnimations.coins()}

👤 <b>Игрок:</b> {user['username']}
👑 <b>VIP:</b> {user['vip_level']}
💰 <b>Баланс:</b> {user['balance']:,} монет

📊 <b>Статистика:</b>
🎯 Побед: {user['total_wins']}
🎮 Игр: {user['total_games']}
📈 Win Rate: {win_rate:.1f}%
🎊 Джекпотов: {user['jackpots']}

{WowAnimations.firework()}
"""
                    send_telegram_message(chat_id, balance_text)
                else:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user['balance'] < 1000:
                    send_telegram_message(chat_id, f"💸 Нужно 1000 монет! Баланс: {user['balance'] if user else 0}")
                    return
                
                send_telegram_message(chat_id, f"{WowAnimations.slots_roll()}\n\n<b>🎲 Бросаем кости...</b>")
                
                update_balance(user_id, -1000)
                user_dice = random.randint(1, 6)
                bot_dice = random.randint(1, 6)
                
                # ВАУ КОСТИ
                if random.random() < 0.1: user_dice = 666  # Демоническая кость
                elif random.random() < 0.05: user_dice = 777  # Ангельская кость
                
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅", 666: "😈", 777: "😇"}
                
                result_text = f"""
🎯 <b>КОСТИ МЕГА ВАУ</b> 🎯

{WowAnimations.firework()}

🎲 <b>ТВОЯ КОСТЬ:</b> {dice_emojis.get(user_dice, '🎲')} <b>{user_dice}</b>
🎲 <b>КОСТЬ КАЗИНО:</b> {dice_emojis.get(bot_dice, '🎲')} <b>{bot_dice}</b>

"""
                
                if user_dice > bot_dice:
                    if user_dice == 777:
                        win_amount = 10000
                        result_text += f"😇 <b>АНГЕЛЬСКАЯ КОСТЬ! СВЯТОЙ ВЫИГРЫШ!</b> 😇\n"
                    elif user_dice == 666:
                        win_amount = 6666
                        result_text += f"😈 <b>ДЕМОНИЧЕСКАЯ КОСТЬ! АДСКОЙ УДАЧИ!</b> 😈\n"
                    else:
                        win_amount = 2000
                    result_text += f"🎉 <b>ПОБЕДА! +{win_amount} монет!</b>\n"
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
                result_text += f"\n💰 <b>Баланс:</b> {user['balance']:,} монет"
                
                send_telegram_message(chat_id, result_text)
            
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user['balance'] < 500:
                    send_telegram_message(chat_id, f"💸 Нужно 500 монет! Баланс: {user['balance'] if user else 0}")
                    return
                
                send_telegram_message(chat_id, f"{WowAnimations.slots_roll()}\n\n<b>🎪 Вращаем барабаны...</b>")
                
                update_balance(user_id, -500)
                
                symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '⭐', '🔥', '👑', '😈', '😇']
                weights = [15, 14, 13, 12, 10, 8, 6, 5, 4, 2, 1]
                slots = [random.choices(symbols, weights=weights)[0] for _ in range(3)]
                
                slots_display = f"""
🎪 <b>МЕГА АВТОМАТЫ ВАУ</b> 🎪

┌───────────┐
│   {slots[0]} {slots[1]} {slots[2]}   │
└───────────┘
"""
                
                if slots[0] == slots[1] == slots[2]:
                    if slots[0] == '👑':
                        win_amount = 25000
                        result_text = f"{slots_display}\n🎊 <b>КОРОЛЕВСКИЙ ДЖЕКПОТ! 👑</b> 🎊\n+{win_amount} монет! 💰"
                        update_jackpot(5000)
                    elif slots[0] == '😇':
                        win_amount = 15000
                        result_text = f"{slots_display}\n😇 <b>АНГЕЛЬСКИЙ ВЫИГРЫШ!</b> 😇\n+{win_amount} монет! 💰"
                    elif slots[0] == '😈':
                        win_amount = 6666
                        result_text = f"{slots_display}\n😈 <b>ДЕМОНИЧЕСКИЙ ВЫИГРЫШ!</b> 😈\n+{win_amount} монет! 💰"
                    elif slots[0] == '💎':
                        win_amount = 10000
                        result_text = f"{slots_display}\n💎 <b>АЛМАЗНЫЙ ВЫИГРЫШ!</b> 💎\n+{win_amount} монет! 💰"
                    else:
                        win_amount = 2000
                        result_text = f"{slots_display}\n🎉 <b>БОЛЬШОЙ ВЫИГРЫШ!</b> 🎉\n+{win_amount} монет! 💰"
                    update_balance(user_id, win_amount)
                
                elif slots[0] == slots[1] or slots[1] == slots[2]:
                    win_amount = 750
                    update_balance(user_id, win_amount)
                    result_text = f"{slots_display}\n🎉 <b>Выигрыш! Два одинаковых!</b>\n+{win_amount} монет! 💰"
                
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
                result_text += f"\n\n💰 <b>Баланс:</b> {user['balance']:,} монет"
                
                send_telegram_message(chat_id, result_text)
            
            elif text == "/jackpot":
                user = get_user(user_id)
                jackpot_amount = get_jackpot()
                
                if not user or user['balance'] < 2000:
                    send_telegram_message(chat_id, f"💸 Для джекпота нужно 2000 монет! Баланс: {user['balance'] if user else 0}")
                    return
                
                send_telegram_message(chat_id, f"🎰 <b>ДЖЕКПОТ РАЗЫГРЫВАЕТСЯ!</b>\n💎 <b>Сумма: {jackpot_amount:,} монет</b>\n\n{WowAnimations.firework()}")
                
                update_balance(user_id, -2000)
                
                if random.random() < 0.03:  # 3% шанс
                    win_text = f"""
🎊 🎊 🎊 <b>ДЖЕКПОТ ВАУУУУ!!!</b> 🎊 🎊 🎊

{WowAnimations.firework()}

<b>💎 {username} ВЫИГРАЛ ДЖЕКПОТ!</b> 💎
<b>💰 СУММА: {jackpot_amount:,} МОНЕТ!</b>

{WowAnimations.coins()}

<b>🎉 ПОЗДРАВЛЯЕМ!</b> 🎉
"""
                    update_balance(user_id, jackpot_amount)
                    update_jackpot(-jackpot_amount + 25000)
                    
                    conn = sqlite3.connect('casino.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET jackpots = jackpots + 1, total_wins = total_wins + 1, total_games = total_games + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                else:
                    win_text = f"""
😔 <b>Джекпот не выпал...</b>

Но не расстраивайся! Джекпот растет:
💎 <b>Теперь: {jackpot_amount + 2000:,} монет</b>

Попробуй еще раз! 🍀
"""
                    update_jackpot(2000)
                
                user = get_user(user_id)
                win_text += f"\n💰 <b>Твой баланс:</b> {user['balance']:,} монет"
                
                send_telegram_message(chat_id, win_text)
            
            elif text == "/top":
                conn = sqlite3.connect('casino.db')
                cursor = conn.cursor()
                cursor.execute('SELECT username, balance, vip_level, jackpots FROM users ORDER BY balance DESC LIMIT 10')
                top_users = cursor.fetchall()
                conn.close()
                
                jackpot = get_jackpot()
                
                top_text = f"""
👑 <b>ТОП ЛЕГЕНД ВАУ</b> 👑

💎 <b>Джекпот: {jackpot:,} монет</b>

"""
                
                for i, (username, balance, vip_level, jackpots) in enumerate(top_users, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    top_text += f"\n{medal} <b>{username}</b>\n   💰 {balance:,} монет | {vip_level}\n   🎊 Джекпотов: {jackpots}\n"
                
                top_text += f"\n{WowAnimations.firework()}"
                
                send_telegram_message(chat_id, top_text)
            
            else:
                send_telegram_message(chat_id, "❌ Неизвестная команда. Напиши /start")
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        return jsonify({"status": "error"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
