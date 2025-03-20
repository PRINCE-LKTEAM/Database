import telebot
import requests
import json
import time
import logging
import os
from telebot.types import InputMediaPhoto
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
USER_ID = 6948812798  # Replace with your Telegram ID
STORAGE_FILE = 'allowed_groups.json'
bot = telebot.TeleBot("7573676656:AAERmQIXZX930ZOtyOrIcG890pf907vjvvU")

# Persistent group storage functions
def load_allowed_groups():
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading groups: {e}")
        return set()

def save_allowed_groups(groups):
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(list(groups), f)
    except Exception as e:
        logger.error(f"Error saving groups: {e}")

allowed_groups = load_allowed_groups()

# Configure requests session with retry logic
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
session.mount('https://', HTTPAdapter(max_retries=retry))

def check_group(message):
    if message.chat.type == "private":
        return True
    if message.chat.id in allowed_groups:
        return True
    else:
        bot.reply_to(message, "🚫 Group not allowed")
        return False

def send_processing(message, text):
    """Safely send processing message with error handling"""
    try:
        return bot.send_message(
            message.chat.id,
            f"⏳ {text}",
            reply_to_message_id=message.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending processing message: {e}")
        return None

def safe_delete_message(chat_id, message_id):
    """Safely delete message with error handling"""
    try:
        if message_id and chat_id:
            bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.warning(f"Error deleting message: {e}")

def handle_api_request(message, url, processing_text, success_callback):
    """Generic API request handler with retries and error handling"""
    if not check_group(message):
        return

    processing_msg = None
    try:
        processing_msg = send_processing(message, processing_text)
        response = session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(data.get("message", "Unknown API error"))
        
        success_callback(message, data)
        
    except requests.exceptions.Timeout:
        error_msg = "⌛ Request timed out. Please try again later."
    except requests.exceptions.RequestException as e:
        error_msg = f"🌐 Network error: {str(e)}"
    except json.JSONDecodeError:
        error_msg = "📄 Invalid response format from API"
    except ValueError as e:
        error_msg = f"🚨 Error: {str(e)}"
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
    finally:
        if processing_msg:
            safe_delete_message(processing_msg.chat.id, processing_msg.message_id)
        
    if 'error_msg' in locals():
        try:
            bot.reply_to(message, error_msg)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

# Group management commands
@bot.message_handler(commands=['allowgroup'])
def allow_group(message):
    if message.from_user.id != USER_ID:
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    if message.chat.type != "private":
        allowed_groups.add(message.chat.id)
        save_allowed_groups(allowed_groups)
        bot.reply_to(message, "✅ This group is now allowed to use the bot.")
    else:
        bot.reply_to(message, "⚠️ This command can only be used in groups")

@bot.message_handler(commands=['disallowgroup'])
def disallow_group(message):
    if message.from_user.id != USER_ID:
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    if message.chat.type != "private":
        allowed_groups.discard(message.chat.id)
        save_allowed_groups(allowed_groups)
        bot.reply_to(message, "🚫 This group is now disallowed from using the bot.")
    else:
        bot.reply_to(message, "⚠️ This command can only be used in groups")

# Command handlers
@bot.message_handler(commands=['start', 'cmd', 'help'])
def send_welcome(message):
    if not check_group(message):
        return
        
    welcome_text = (
        "🔥 *Free Fire Info Bot*\n\n"
        "📋 *Available Commands:*\n"
        "/accdate <uid> <region> - Get account creation date\n"
        "/visit <uid> - Boost account visitors\n"
        "/ffinfo <playerid> - Get player info\n"
        "/baninfo <playerid> - Check ban status\n"
        "/mapinfo <region> <mapcode> - Get map details\n"
        "/decode <token> - Decode JWT token\n"
        "/events <region> - Show current events\n"
        "/genimg <prompt> - Generate image\n"
        "/ffstatus - Check Free Fire server status\n"
        "/ytinfo <url> - Get YouTube video info\n"
        "/repoinfo <user> <repo> - Get GitHub repo info\n"
    )
    try:
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

@bot.message_handler(commands=['accdate'])
def handle_accdate(message):
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if len(args) < 2:
            raise ValueError("Missing UID or region")
            
        uid, region = args[0], args[1]
        url = f"https://lk-team-ff-acc-creation-date.vercel.app/ffaccdate?uid={uid}&region={region}"
        handle_api_request(message, url, "Fetching account information...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['visit'])
def handle_visit(message):
    if not check_group(message):
        return

    def send_visits(uid):
        success_count = 0
        error_count = 0
        last_response = None
        
        for i in range(1, 51):
            try:
                url = f"https://foxvisit.vercel.app/visit?uid={uid}&attempt={i}"
                response = session.get(url, timeout=5)
                response.raise_for_status()
                last_response = response.json()
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Visit attempt {i} failed: {e}")
            
        return success_count, error_count, last_response
    
    def success_callback(msg, data):
        success_count, error_count, last_response = data
        summary = (
            f"🚀 *Visit Boost Results*\n\n"
            f"✅ Successful attempts: `{success_count}`\n"
            f"❌ Failed attempts: `{error_count}`\n"
            f"📄 Last response:\n"
            f"```json\n{json.dumps(last_response, indent=4)}\n```"
        )
        bot.reply_to(msg, summary, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Missing UID")
            
        uid = args[0]
        processing_text = f"🔥 Boosting visits for UID: {uid} (0/50)"
        
        processing_msg = send_processing(message, processing_text)
        
        def visit_task():
            try:
                results = send_visits(uid)
                success_callback(message, results)
            finally:
                safe_delete_message(processing_msg.chat.id, processing_msg.message_id)
        
        bot.worker_pool.put(visit_task)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['ffinfo'])
def handle_ffinfo(message):
    """Player info handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Missing player ID")
            
        player_id = args[0]
        url = f"https://ffinfo-temp.vercel.app/api/player-info?id={playet_id}
        handle_api_request(message, url, "Fetching player stats...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['baninfo'])
def handle_baninfo(message):
    """Ban info handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Missing player ID")
            
        player_id = args[0]
        url = f"https://freefirebancheckapi.vercel.app/api/player_info/{player_id}"
        handle_api_request(message, url, "Checking ban status...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['decode'])
def handle_decode(message):
    """JWT decoder handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Missing token")
            
        token = args[0]
        url = f"https://decode-jwt-lkteam.vercel.app/decode_jwt?token={token}"
        handle_api_request(message, url, "Decoding JWT token...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['ptinemogff'])
def handle_events(message):
    """Events handler with media support"""
    def success_callback(msg, data):
        try:
            # Send JSON response in chunks
            formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
            max_length = 4096  # Telegram message limit
            
            for i in range(0, len(formatted_json), max_length):
                chunk = formatted_json[i:i+max_length]
                bot.send_message(msg.chat.id, f"```json\n{chunk}\n```", parse_mode='Markdown')
            
            # Handle media
            media_group = []
            for event in data.get('events', []):
                if img_url := event.get('src'):
                    if img_url.startswith(('http://', 'https://')):
                        media_group.append(InputMediaPhoto(img_url))
                        
                        # Send in batches of 10
                        if len(media_group) >= 10:
                            bot.send_media_group(msg.chat.id, media_group)
                            media_group = []
            
            # Send remaining media
            if media_group:
                bot.send_media_group(msg.chat.id, media_group)
                
        except Exception as e:
            logger.error(f"Error processing events response: {e}")
            bot.reply_to(msg, "⚠ Error processing events data")
    
    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Missing region")
            
        region = args[0]
        url = f"https://ff-event-nine.vercel.app/events?region={region}"
        handle_api_request(message, url, "Fetching events...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['genimg'])
def handle_genimg(message):
    """Image generation handler"""
    def success_callback(msg, data):
        try:
            if 'image_url' in data:
                bot.send_photo(msg.chat.id, data['image_url'])
            if 'details' in data:
                bot.reply_to(msg, f"```json\n{json.dumps(data['details'], indent=4)}\n```", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending generated image: {e}")
    
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Missing prompt")
            
        prompt = args[1]
        url = f"https://lk-team-imagegen.vercel.app/generate_image?api_key=globalkey&prompt={requests.utils.quote(prompt)}"
        handle_api_request(message, url, "Generating image...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['ffstatus'])
def handle_ffstatus(message):
    """Free Fire server status handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    url = "https://ffstatusapi.vercel.app/api/freefire/normal/overview"
    handle_api_request(message, url, "Checking Free Fire server status...", success_callback)

@bot.message_handler(commands=['ytinfo'])
def handle_ytinfo(message):
    """YouTube video info handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Missing YouTube URL")
            
        yt_url = args[1]
        encoded_url = requests.utils.quote(yt_url)
        url = f"https://lkteam-yt-info-api-v1.vercel.app/video_info?url={encoded_url}"
        handle_api_request(message, url, "Fetching YouTube video info...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['repoinfo'])
def handle_repoinfo(message):
    """GitHub repo info handler"""
    def success_callback(msg, data):
        formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
        bot.reply_to(msg, formatted, parse_mode='Markdown')
    
    try:
        args = message.text.split()[1:]
        if len(args) < 2:
            raise ValueError("Missing username or repository name")
            
        username, reponame = args[0], args[1]
        url = f"https://githubrepoinfo-lkteam.vercel.app/repo?user={username}&repo={reponame}"
        handle_api_request(message, url, "Fetching GitHub repository info...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['mapinfo'])
def handle_mapinfo(message):
    """Map info handler"""
    def success_callback(msg, data):
        try:
            formatted = f"```json\n{json.dumps(data, indent=4, ensure_ascii=False)}\n```"
            bot.reply_to(msg, formatted, parse_mode='Markdown')
            if data.get('share_img'):
                bot.send_photo(msg.chat.id, data['share_img'])
        except Exception as e:
            logger.error(f"Error sending map info: {e}")

    try:
        args = message.text.split()[1:]
        if not args:
            raise ValueError("Need to provide a map code")
            
        mapcode = args[0]
        url = f"https://ffmapinfo-lk-team.vercel.app/get_map_info?map_code={requests.utils.quote(mapcode)}"
        handle_api_request(message, url, "Fetching map details...", success_callback)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def start_polling():
    """Robust polling with automatic recovery"""
    while True:
        try:
            logger.info(f"Starting bot with {len(allowed_groups)} allowed groups")
            bot.polling(non_stop=True, interval=1, timeout=30)
        except Exception as e:
            logger.error(f"Polling error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    start_polling()