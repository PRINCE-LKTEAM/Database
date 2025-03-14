import telebot
import requests
import json
import time
from requests.exceptions import RequestException

bot = telebot.TeleBot("7561249160:AAFq96c7Izr86R2fwjcOUZWb59ffSIng4SU")  # Replace with your token

BASE_URL = "https://freefire-virusteam.vercel.app"
DEFAULT_KEY = "zeusthug"
FOOTER = "\n\nMADE BY: https://t.me/lkteammm"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Welcome to the Free Fire Spam Bot!\n\n"
        "Use /request command followed by UID and region (me/ind/vn)\n"
        "Example: /request 1239493939 me"
        f"{FOOTER}"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['request'])
def handle_request(message):
    sent_msg = None
    try:
        parts = message.text.split()
        if len(parts) != 3:
            reply = f"Invalid format. Use: /request {{UID}} {{region}}{FOOTER}\nExample: /request 12345678 me"
            bot.reply_to(message, reply)
            return

        _, uid, region = parts
        region = region.lower()

        if region not in ['me', 'ind', 'vn']:
            bot.reply_to(message, f"Invalid region. Available regions: me, ind, vn{FOOTER}")
            return

        processing_msg = f"⏳ Sending request to `{uid}`...{FOOTER}"
        sent_msg = bot.reply_to(message, processing_msg, parse_mode='Markdown')

        url = f"{BASE_URL}/{region}/spamkb?key={DEFAULT_KEY}&uid={uid}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'Success':
            user_data = data.get("UID Validated - API connected", {})
            filtered_data = {
                "status": data.get('status'),
                "Name": user_data.get('Name'),
                "Level": user_data.get('Level'),
                "Region": user_data.get('Region')
            }
            json_response = json.dumps(filtered_data, indent=2)
            result_text = f"```json\n{json_response}\n```{FOOTER}"
        else:
            result_text = f"❌ Error: {data.get('status', 'Unknown error')}{FOOTER}"

        bot.delete_message(message.chat.id, sent_msg.message_id)
        bot.send_message(message.chat.id, result_text, parse_mode='Markdown')

    except RequestException as e:
        error_msg = f"🔴 Request Failed{FOOTER}"
        self.cleanup_and_send(message, sent_msg, error_msg)
        
    except json.JSONDecodeError:
        error_msg = f"🔴 Invalid server response{FOOTER}"
        self.cleanup_and_send(message, sent_msg, error_msg)
        
    except Exception as e:
        error_msg = f"🔴 An unexpected error occurred{FOOTER}"
        self.cleanup_and_send(message, sent_msg, error_msg)

def cleanup_and_send(self, message, sent_msg, error_msg):
    try:
        if sent_msg:
            bot.delete_message(message.chat.id, sent_msg.message_id)
    except:
        pass
    bot.send_message(message.chat.id, error_msg, parse_mode='Markdown')

def run_bot():
    while True:
        try:
            print("Bot is starting...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Bot crashed: {str(e)}")
            print("Attempting restart in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()