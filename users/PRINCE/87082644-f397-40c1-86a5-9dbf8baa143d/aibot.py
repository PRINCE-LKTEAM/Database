import requests
import json
import telebot
import time
import sys
import logging

API_TOKEN = '7555332598:AAH8qZyfGkxs72nftNEyfIG8NiamwR5p42Y'  # Replace with your Telegram bot token
bot = telebot.TeleBot(API_TOKEN)

url = "https://lk-team-aipro.vercel.app"
headers = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    'Content-Type': "application/json",
    'sec-ch-ua': "\"Not A(Brand\";v=\"8\", \"Chromium\";v=\"132\"",
    'sec-ch-ua-platform': "\"Android\"",
    'sec-ch-ua-mobile': "?1",
    'origin': "https://lk-team-aipro.vercel.app",
    'sec-fetch-site': "same-origin",
    'sec-fetch-mode': "cors",
    'sec-fetch-dest': "empty",
    'referer': "https://lk-team-aipro.vercel.app/",
    'accept-language': "en-US,en;q=0.9,es-US;q=0.8,es;q=0.7"
}

# Function to call the API
def get_ai_response(question):
    payload = {"question": question}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response.json().get("response", "No response from AI.")

# Command to start the bot
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! I'm your friendly AI assistant 🤖\nSend me any question, and I will provide an answer. Ask me anything!")

# Command to ask a question
@bot.message_handler(commands=['ask'])
def ask_question(message):
    question = message.text.replace("/ask", "").strip()
    
    if question:
        # Inform user that the bot is thinking...
        thinking_message = bot.send_message(message.chat.id, "Thinking... 🤔 Please wait a moment while I fetch the answer!")
        
        # Get the AI response
        ai_response = get_ai_response(question)
        
        # Edit the message to show the AI response
        bot.edit_message_text(f"**Question:** {question}\n\n**AI Response:**\n{ai_response}", message.chat.id, thinking_message.message_id, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Please ask a question after the /ask command. For example, `/ask Who are you?`")

# Disable any responses to messages that don't start with /ask
@bot.message_handler(func=lambda message: not message.text.startswith("/ask"))
def no_reply(message):
    pass

# Auto restart function
def start_bot():
    while True:
        try:
            print("Starting bot...")
            bot.polling(non_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Wait for 5 seconds before restarting the bot

# Start the bot with auto restart
if __name__ == '__main__':
    start_bot()