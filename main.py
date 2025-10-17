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
            balance INTEGER DEFAULT 1000,
            total_wins INTEGER DEFAULT 0
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
    return user

def create_user(user_id, username):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)', 
                   (user_id, username, 1000))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
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
    return "🎰 Casino Bot is RUNNING! 🚀"

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
                response = f"""🎰 <b>CASINO BOT</b> 🎰

Привет, {username}! 👋

💰 <b>Баланс:</b> {user[2]} монет

🎮 <b>Команды:</b>
🎯 /dice - Кости (100 монет)
🎪 /slots - Автоматы (50 монет)
💼 /balance - Баланс

🚀 <b>Бот работает 24/7!</b>"""
                send_telegram_message(chat_id, response)
                
            elif text == "/balance":
                user = get_user(user_id)
                if user:
                    send_telegram_message(chat_id, f"💰 <b>Баланс:</b> {user[2]} монет")
                else:
                    send_telegram_message(chat_id, "❌ Напиши /start")
                    
            elif text == "/dice":
                user = get_user(user_id)
                if not user or user[2] < 100:
                    send_telegram_message(chat_id, "❌ Недостаточно средств! Нужно 100 монет")
                else:
                    update_balance(user_id, -100)
                    user_dice = random.randint(1, 6)
                    bot_dice = random.randint(1, 6)
                    
                    if user_dice > bot_dice:
                        win = 150
                        update_balance(user_id, win)
                        result = f"🎉 <b>ПОБЕДА! +{win} монет!</b>"
                    elif user_dice < bot_dice:
                        result = "😔 <b>Проигрыш</b>"
                    else:
                        update_balance(user_id, 100)
                        result = "🤝 <b>Ничья! Ставка возвращена</b>"
                    
                    user = get_user(user_id)
                    send_telegram_message(chat_id, f"🎯 <b>Кости</b>\n\n🎲 Ты: {user_dice}\n🎲 Казино: {bot_dice}\n\n{result}\n\n💰 <b>Баланс:</b> {user[2]} монет")
            
            elif text == "/slots":
                user = get_user(user_id)
                if not user or user[2] < 50:
                    send_telegram_message(chat_id, "❌ Недостаточно средств! Нужно 50 монет")
                else:
                    update_balance(user_id, -50)
                    symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎']
                    slots = [random.choice(symbols) for _ in range(3)]
                    
                    display = f"🎪 <b>АВТОМАТЫ</b>\n┌───────┐\n│ {slots[0]} {slots[1]} {slots[2]} │\n└───────┘"
                    
                    if slots[0] == slots[1] == slots[2]:
                        win = 200
                        update_balance(user_id, win)
                        result = f"{display}\n🎊 <b>ДЖЕКПОТ! +{win} монет!</b> 💰"
                    elif slots[0] == slots[1] or slots[1] == slots[2]:
                        win = 75
                        update_balance(user_id, win)
                        result = f"{display}\n🎉 <b>Выигрыш! +{win} монет!</b> 💰"
                    else:
                        result = f"{display}\n😔 <b>Повезет в следующий раз!</b>"
                    
                    user = get_user(user_id)
                    send_telegram_message(chat_id, f"{result}\n\n💰 <b>Баланс:</b> {user[2]} монет")
            
            else:
                send_telegram_message(chat_id, "❌ Неизвестная команда. Напиши /start")
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
