import telebot
import requests
import schedule
import time
import threading
import json
from datetime import datetime

TOKEN = "7256058679:AAHKW78fl6HFOcjZTMIrOoU5yCQpr0KHEMo"
bot = telebot.TeleBot(TOKEN)

# Define both APIs
API_URL_V1 = "https://likes-api-lk-team.vercel.app/like?uid={uid}&server_name={region}"
API_URL_V2 = "https://likes-api-v2.onrender.com/like?uid={uid}&count={count}"
ALLOWED_REGIONS = ["ME", "SG", "BD"]
DATA_FILE = "activated_users.json"
ADMIN_ID = 6948812798  # Admin Telegram ID

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Migrate old data format
            for chat_id, user_info in data.items():
                if "api_version" not in user_info:
                    user_info["api_version"] = "v1"
            return data
    except FileNotFoundError:
        return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_timestamp():
    now = datetime.now()
    return now.strftime("%d-%m-%Y %H:%M:%S")

activated_users = load_users()

@bot.message_handler(commands=["start"])
def send_welcome(message):
    welcome_text = (
        "✨ *Welcome to the Likes Bot!* ✨\n\n"
        "💫 Send likes to your favorite players with ease!\n"
        "📱 Use /help to see all available commands.\n\n"
        "🌟 *Created with ❤️ by @lkteammm* 🌟"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=["help"])
def send_help(message):
    help_text = (
        "🔰 *Bot Commands* 🔰\n\n"
        "➡️ /like <UID> <region> – Send likes manually\n"
        "➡️ /activate <UID> <region> – Enable daily auto-likes\n"
        "➡️ /api <version> – Switch API version (v1 or v2)\n"
        "➡️ /status – Check your activation status\n"
        "➡️ /help – Show this message\n\n"
        "✅ *Supported Regions:* ME, SG, BD\n\n"
        "🌟 Get daily likes automatically with /activate!\n"
        "💡 *Questions?* Contact @lkteammm"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=["api"])
def switch_api(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "⚠️ *Usage:* /api <version> (v1 or v2)", parse_mode="Markdown")
            return

        version = parts[1].lower()  
        if version not in ["v1", "v2"]:  
            bot.reply_to(message, "❌ *Invalid version!* Use `v1` or `v2`", parse_mode="Markdown")  
            return  
          
        chat_id = str(message.chat.id)  
        user_data = activated_users.get(chat_id, {})  
        user_data["api_version"] = version  
        activated_users[chat_id] = user_data  
        save_users(activated_users)  
          
        success_text = (
            f"✅ *API SWITCHED SUCCESSFULLY!* ✅\n\n"
            f"🔄 *New API Version:* `{version}`\n"
            f"⏱️ *Time:* `{get_timestamp()}`\n\n"
            f"💫 *Powered by Likes Bot* 💫"
        )
        bot.reply_to(message, success_text, parse_mode="Markdown")  
      
    except Exception as e:  
        bot.reply_to(message, "⚠️ *Error occurred while switching API*", parse_mode="Markdown")

@bot.message_handler(commands=["like"])
def send_likes(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "⚠️ *Usage:* /like <UID> <region>", parse_mode="Markdown")
            return

        uid, region = parts[1], parts[2].upper()  
        chat_id = str(message.chat.id)  
        user_data = activated_users.get(chat_id, {})  
        api_version = user_data.get("api_version", "v1")  

        # API selection  
        if api_version == "v1":  
            if region not in ALLOWED_REGIONS:
                regions_text = ", ".join(f"`{r}`" for r in ALLOWED_REGIONS)
                error_text = (
                    f"❌ *REGION NOT AVAILABLE* ❌\n\n"
                    f"🌍 *Region `{region}` is not supported*\n"
                    f"✅ *Available Regions:* {regions_text}\n\n"
                    f"⚠️ Please try again with a supported region"
                )
                bot.reply_to(message, error_text, parse_mode="Markdown")
                return
                
            api_url = API_URL_V1.format(uid=uid, region=region)  
        else:  
            count = 100  # Default count for v2  
            api_url = API_URL_V2.format(uid=uid, count=count)  

        processing_text = (
            f"⏳ *PROCESSING REQUEST* ⏳\n\n"
            f"🆔 *UID:* `{uid}`\n"
            f"🌍 *Region:* `{region}`\n"
            f"🔄 *API Version:* `{api_version}`\n\n"
            f"⌛ *Please wait...*"
        )
        bot.reply_to(message, processing_text, parse_mode="Markdown")
        
        # Try to make the API request with timeout
        try:
            response = requests.get(api_url, timeout=10)
            
            # Handle HTTP errors
            if response.status_code >= 500:
                bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")
                return
                
            response.raise_for_status()
            response_data = response.json()  

            if api_version == "v1":  
                if response_data.get("status") == 1:  
                    text = (  
                        f"🎉 *LIKES SENT SUCCESSFULLY!* 🎉\n\n"  
                        f"👤 *Player:* `{response_data['PlayerNickname']}`\n"  
                        f"🆔 *UID:* `{response_data['UID']}`\n"  
                        f"❤️ *Likes Before:* `{response_data['Likesbefore']}`\n"  
                        f"💙 *Likes Sent:* `{response_data['LikesSent']}`\n"  
                        f"💛 *Likes After:* `{response_data['Likesafter']}`\n"  
                        f"🌍 *Region:* `{region}`\n"
                        f"⏱️ *Time:* `{get_timestamp()}`\n\n"
                        f"💫 *Powered by Likes Bot* 💫"
                    )  
                    bot.reply_to(message, text, parse_mode="Markdown")  
                else:  
                    bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")  
            else:  
                text = (  
                    f"🎉 *LIKES SENT SUCCESSFULLY!* 🎉\n\n"  
                    f"👤 *Player:* `{response_data.get('name', 'N/A')}`\n"  
                    f"🆔 *UID:* `{response_data.get('uid', 'N/A')}`\n"  
                    f"❤️ *Likes Before:* `{response_data.get('likes_before', 'N/A')}`\n"  
                    f"💙 *Likes Sent:* `{response_data.get('likes_added', 'N/A')}`\n"  
                    f"💛 *Likes After:* `{response_data.get('likes_after', 'N/A')}`\n"  
                    f"🌍 *Region:* `{response_data.get('region', 'N/A')}`\n"
                    f"⏱️ *Time:* `{get_timestamp()}`\n\n"
                    f"💫 *Powered by Likes Bot* 💫"
                )  
                bot.reply_to(message, text, parse_mode="Markdown")  
        
        except requests.Timeout:
            bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")
        except requests.HTTPError as http_err:
            if http_err.response.status_code >= 500:
                bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")

    except Exception as e:  
        bot.reply_to(message, "❌ *Failed to send likes*", parse_mode="Markdown")

@bot.message_handler(commands=["status"])
def check_status(message):
    chat_id = str(message.chat.id)
    if chat_id not in activated_users:
        bot.reply_to(message, "❌ *You have no active auto-likes setup*", parse_mode="Markdown")
        return
    
    user_data = activated_users[chat_id]
    status_text = (
        f"📊 *YOUR AUTO-LIKES STATUS* 📊\n\n"
        f"👤 *UID:* `{user_data.get('uid', 'Not set')}`\n"
        f"🌍 *Region:* `{user_data.get('region', 'Not set')}`\n"
        f"🔄 *API Version:* `{user_data.get('api_version', 'v1')}`\n"
        f"⏱️ *Next Auto-Like:* `00:00 UTC`\n\n"
        f"✅ *Your auto-likes are active!*"
    )
    bot.reply_to(message, status_text, parse_mode="Markdown")

@bot.message_handler(commands=["activate"])
def activate_user(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "⚠️ *Usage:* /activate <UID> <region>", parse_mode="Markdown")
            return

        uid, region = parts[1], parts[2].upper()  
        if region not in ALLOWED_REGIONS:
            regions_text = ", ".join(f"`{r}`" for r in ALLOWED_REGIONS)
            error_text = (
                f"❌ *REGION NOT AVAILABLE* ❌\n\n"
                f"🌍 *Region `{region}` is not supported*\n"
                f"✅ *Available Regions:* {regions_text}\n\n"
                f"⚠️ Please try again with a supported region"
            )
            bot.reply_to(message, error_text, parse_mode="Markdown")
            return

        processing_text = (
            f"⏳ *ACTIVATING AUTO-LIKES* ⏳\n\n"
            f"🆔 *UID:* `{uid}`\n"
            f"🌍 *Region:* `{region}`\n\n"
            f"⌛ *Please wait...*"
        )
        bot.reply_to(message, processing_text, parse_mode="Markdown")

        chat_id = str(message.chat.id)  
        activated_users[chat_id] = {  
            "uid": uid,  
            "region": region,  
            "api_version": activated_users.get(chat_id, {}).get("api_version", "v1"),
            "activated_at": get_timestamp()
        }  
        save_users(activated_users)  
        
        success_text = (
            f"✅ *AUTO-LIKES ACTIVATED!* ✅\n\n"
            f"👤 *UID:* `{uid}`\n"
            f"🌍 *Region:* `{region}`\n"
            f"🔄 *API Version:* `{activated_users[chat_id]['api_version']}`\n"
            f"📅 *Activated On:* `{activated_users[chat_id]['activated_at']}`\n"
            f"⏱️ *Daily Likes At:* `00:00 UTC`\n\n"
            f"🎯 *Your account is now set for daily likes!*\n"
            f"💫 *Powered by Likes Bot* 💫"
        )
        
        bot.reply_to(message, success_text, parse_mode="Markdown")  
      
    except Exception as e:  
        bot.reply_to(message, "⚠️ *Error occurred while activating auto-likes*", parse_mode="Markdown")

# Admin Commands
@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ *This command is admin-only*", parse_mode="Markdown")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ *Usage:* /broadcast <message>", parse_mode="Markdown")
        return
    
    broadcast_text = parts[1]
    formatted_broadcast = (
        f"📢 *ADMIN BROADCAST* 📢\n\n"
        f"{broadcast_text}\n\n"
        f"⏱️ *Sent at:* `{get_timestamp()}`\n"
        f"🔔 *From:* Admin"
    )
    
    success_count = 0
    total_count = len(activated_users)
    
    processing_text = (
        f"⏳ *BROADCASTING MESSAGE* ⏳\n\n"
        f"📨 *Total Recipients:* `{total_count}`\n"
        f"⌛ *Sending...*"
    )
    bot.reply_to(message, processing_text, parse_mode="Markdown")
    
    for chat_id in activated_users:
        try:
            bot.send_message(int(chat_id), formatted_broadcast, parse_mode="Markdown")
            success_count += 1
            time.sleep(0.1)  # Prevent flood limits
        except Exception:
            pass
    
    result_text = (
        f"✅ *BROADCAST COMPLETED* ✅\n\n"
        f"📊 *Stats:*\n"
        f"📨 *Total Recipients:* `{total_count}`\n"
        f"✅ *Successfully Sent:* `{success_count}`\n"
        f"❌ *Failed:* `{total_count - success_count}`\n"
        f"⏱️ *Completed at:* `{get_timestamp()}`"
    )
    bot.reply_to(message, result_text, parse_mode="Markdown")

@bot.message_handler(commands=["sendto"])
def send_to_specific(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ *This command is admin-only*", parse_mode="Markdown")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ *Usage:* /sendto <chat_id> <message>", parse_mode="Markdown")
        return
    
    try:
        target_chat_id = int(parts[1])
        message_text = parts[2]
        
        formatted_message = (
            f"📨 *ADMIN MESSAGE* 📨\n\n"
            f"{message_text}\n\n"
            f"⏱️ *Sent at:* `{get_timestamp()}`\n"
            f"🔔 *From:* Admin"
        )
        
        bot.send_message(target_chat_id, formatted_message, parse_mode="Markdown")
        
        success_text = (
            f"✅ *MESSAGE SENT* ✅\n\n"
            f"👤 *Recipient:* `{target_chat_id}`\n"
            f"⏱️ *Sent at:* `{get_timestamp()}`"
        )
        bot.reply_to(message, success_text, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ *Failed to send message: {str(e)}*", parse_mode="Markdown")

@bot.message_handler(commands=["stats"])
def show_stats(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ *This command is admin-only*", parse_mode="Markdown")
        return
    
    total_users = len(activated_users)
    api_v1_count = sum(1 for user in activated_users.values() if user.get("api_version", "v1") == "v1")
    api_v2_count = sum(1 for user in activated_users.values() if user.get("api_version", "v1") == "v2")
    
    regions_count = {}
    for region in ALLOWED_REGIONS:
        regions_count[region] = sum(1 for user in activated_users.values() if user.get("region", "") == region)
    
    regions_text = "\n".join(f"🌍 *{region}:* `{count}`" for region, count in regions_count.items())
    
    stats_text = (
        f"📊 *BOT STATISTICS* 📊\n\n"
        f"👥 *Total Users:* `{total_users}`\n\n"
        f"🔄 *API Usage:*\n"
        f"➡️ *v1:* `{api_v1_count}`\n"
        f"➡️ *v2:* `{api_v2_count}`\n\n"
        f"🌐 *Regions:*\n{regions_text}\n\n"
        f"⏱️ *Generated at:* `{get_timestamp()}`"
    )
    
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.message_handler(commands=["admin"])
def admin_help(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ *This command is admin-only*", parse_mode="Markdown")
        return
    
    admin_help_text = (
        f"🔰 *ADMIN COMMANDS* 🔰\n\n"
        f"➡️ /broadcast <message> – Send to all users\n"
        f"➡️ /sendto <chat_id> <message> – Send to specific user\n"
        f"➡️ /stats – Show bot statistics\n"
        f"➡️ /export – Export user database\n"
        f"➡️ /admin – Show this help\n\n"
        f"⚙️ *Your admin ID:* `{ADMIN_ID}`"
    )
    
    bot.reply_to(message, admin_help_text, parse_mode="Markdown")

@bot.message_handler(commands=["export"])
def export_database(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ *This command is admin-only*", parse_mode="Markdown")
        return
    
    try:
        with open(DATA_FILE, "rb") as f:
            bot.send_document(message.chat.id, f, caption="📊 *User Database Export*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ *Error exporting database: {str(e)}*", parse_mode="Markdown")

def auto_like():
    for chat_id, data in activated_users.items():
        if "uid" in data and "region" in data:
            uid = data["uid"]
            region = data["region"]
            api_version = data.get("api_version", "v1")

            try:  
                if api_version == "v1":  
                    api_url = API_URL_V1.format(uid=uid, region=region)  
                else:  
                    api_url = API_URL_V2.format(uid=uid, count=100)  

                try:
                    response = requests.get(api_url, timeout=10)
                    
                    # Handle HTTP errors
                    if response.status_code >= 500:
                        bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")
                        continue
                        
                    response.raise_for_status()
                    response_data = response.json()  

                    if api_version == "v1":  
                        if response_data.get("status") == 1:  
                            text = (  
                                f"🌟 *DAILY AUTO-LIKES SENT!* 🌟\n\n"  
                                f"👤 *Player:* `{response_data['PlayerNickname']}`\n"  
                                f"🆔 *UID:* `{response_data['UID']}`\n"  
                                f"❤️ *Likes Before:* `{response_data['Likesbefore']}`\n"  
                                f"💙 *Likes Sent:* `{response_data['LikesSent']}`\n"  
                                f"💛 *Likes After:* `{response_data['Likesafter']}`\n"  
                                f"🌍 *Region:* `{region}`\n"
                                f"⏱️ *Time:* `{get_timestamp()}`\n\n"
                                f"💯 *See you tomorrow!* 💯"
                            )  
                            bot.send_message(chat_id, text, parse_mode="Markdown")  
                        else:  
                            bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")  
                    else:  
                        text = (  
                            f"🌟 *DAILY AUTO-LIKES SENT!* 🌟\n\n"  
                            f"👤 *Player:* `{response_data.get('name', 'N/A')}`\n"  
                            f"🆔 *UID:* `{response_data.get('uid', 'N/A')}`\n"  
                            f"❤️ *Likes Before:* `{response_data.get('likes_before', 'N/A')}`\n"  
                            f"💙 *Likes Sent:* `{response_data.get('likes_added', 'N/A')}`\n"  
                            f"💛 *Likes After:* `{response_data.get('likes_after', 'N/A')}`\n"  
                            f"🌍 *Region:* `{response_data.get('region', 'N/A')}`\n"
                            f"⏱️ *Time:* `{get_timestamp()}`\n\n"
                            f"💯 *See you tomorrow!* 💯"
                        )  
                        bot.send_message(chat_id, text, parse_mode="Markdown")  
                
                except requests.Timeout:
                    bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")
                except requests.HTTPError as http_err:
                    if http_err.response.status_code >= 500:
                        bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")
                    else:
                        bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")
                except Exception:
                    bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")
                  
            except Exception:  
                bot.send_message(chat_id, "❌ *Failed to send likes*", parse_mode="Markdown")

schedule.every().day.at("00:00").do(auto_like)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

def start_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Bot crashed: {e}")
            time.sleep(5)

start_bot()