import os
import subprocess
import telebot
from telebot import types
import json
import threading
import time
from datetime import datetime
import shutil

# Configuration
API_TOKEN = '7663164510:AAEVptqfCdopRl92MebuqyP97Ka7ESvx1jk'
ADMIN_ID = 6948812798
USER_BOTS_FILE = 'user_bots.json'
RUNNING_BOTS_FILE = 'running_bots.json'

bot = telebot.TeleBot(API_TOKEN)
user_bots = {}
running_bots = {}
temp_data = {}

# Load persistent data
try:
    with open(USER_BOTS_FILE, 'r') as f:
        user_bots = json.load(f)
except FileNotFoundError:
    user_bots = {}

try:
    with open(RUNNING_BOTS_FILE, 'r') as f:
        running_bots = json.load(f)
except FileNotFoundError:
    running_bots = {}

# Utility functions
def save_user_bots():
    with open(USER_BOTS_FILE, 'w') as f:
        json.dump(user_bots, f)

def save_running_bots():
    with open(RUNNING_BOTS_FILE, 'w') as f:
        json.dump(running_bots, f)

def create_user_directory(user_id, bot_name):
    path = f"user_bots/{user_id}/{bot_name}"
    os.makedirs(path, exist_ok=True)
    return path

def send_to_admin(file_path, bot_name, user_id):
    try:
        with open(file_path, 'rb') as f:
            bot.send_document(ADMIN_ID, f, caption=f"🚨 New upload from user #{user_id}\n🤖 Bot: {bot_name}")
    except Exception as e:
        print(f"Error sending to admin: {e}")

def stylish_message(text):
    return f"✨ {text} ✨"

def error_message(text):
    return f"❌ {text} ❌"

def success_message(text):
    return f"✅ {text} ✅"

def create_keyboard(buttons):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

# Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    welcome_text = stylish_message("Welcome to Bot Hosting Service!") + "\n\n"
    welcome_text += "📋 *Available Commands:*\n"
    welcome_text += "▫️ /newbot - Create a new bot\n"
    welcome_text += "▫️ /upload - Upload bot files\n"
    welcome_text += "▫️ /run - Start your bot\n"
    welcome_text += "▫️ /stop - Stop your bot\n"
    welcome_text += "▫️ /restart <name> - Restart a bot\n"
    welcome_text += "▫️ /delete <name> - Delete a bot\n"
    welcome_text += "▫️ /listbots - List your bots\n"
    welcome_text += "▫️ /status <name> - Check bot status\n"
    bot.send_message(user_id, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['newbot'])
def new_bot(message):
    user_id = str(message.from_user.id)
    msg = bot.send_message(user_id, stylish_message("Let's create a new bot!\nPlease choose a name for your bot:"),
                          parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_bot_name)

def process_bot_name(message):
    user_id = str(message.from_user.id)
    bot_name = message.text.strip()
    
    if not bot_name.isalnum() or len(bot_name) > 20:
        bot.send_message(user_id, error_message("Invalid name! Use only alphanumeric characters (max 20)"), 
                         parse_mode='Markdown')
        return
    
    if user_id not in user_bots:
        user_bots[user_id] = {}
    
    if bot_name in user_bots[user_id]:
        bot.send_message(user_id, error_message("Bot name already exists!"), parse_mode='Markdown')
        return
    
    user_bots[user_id][bot_name] = {'main_file': None, 'created': datetime.now().isoformat()}
    temp_data[user_id] = {'current_bot': bot_name, 'awaiting_file': 'python'}
    create_user_directory(user_id, bot_name)
    save_user_bots()
    
    msg = bot.send_message(user_id, success_message(f"Bot '{bot_name}' created!") + "\n\n📤 Please upload your Python file now:",
                          reply_markup=types.ReplyKeyboardRemove(), parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_uploaded_file)

def save_uploaded_file(message):
    user_id = str(message.from_user.id)
    if user_id not in temp_data or 'current_bot' not in temp_data[user_id]:
        bot.send_message(user_id, error_message("Session expired. Start over with /newbot"), parse_mode='Markdown')
        return
    
    bot_name = temp_data[user_id]['current_bot']
    file_type = temp_data[user_id].get('awaiting_file', 'python')
    
    try:
        if message.document:
            if file_type == 'python' and not message.document.file_name.endswith('.py'):
                bot.send_message(user_id, error_message("Please upload a Python (.py) file"), parse_mode='Markdown')
                return
            
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            path = f"user_bots/{user_id}/{bot_name}/"
            filename = message.document.file_name if file_type == 'python' else 'requirements.txt'
            
            with open(path + filename, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            send_to_admin(path + filename, bot_name, user_id)
            
            if file_type == 'python':
                user_bots[user_id][bot_name]['main_file'] = filename
                temp_data[user_id]['awaiting_file'] = 'requirements'
                msg = bot.send_message(user_id, success_message("Python file uploaded!") + "\n\n📤 Now send requirements.txt",
                                      parse_mode='Markdown')
                bot.register_next_step_handler(msg, save_uploaded_file)
            else:
                try:
                    result = subprocess.run(['pip', 'install', '-r', path + 'requirements.txt'], 
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        bot.send_message(user_id, success_message("Dependencies installed!") + "\n\n🛠️ You can now /run your bot",
                                        parse_mode='Markdown')
                    else:
                        error_log = f"```\n{result.stderr[:1500]}...\n```"
                        bot.send_message(user_id, error_message("Installation failed:") + f"\n{error_log}", 
                                         parse_mode='Markdown')
                    del temp_data[user_id]['awaiting_file']
                except Exception as e:
                    bot.send_message(user_id, error_message(f"Installation error: {str(e)}"), parse_mode='Markdown')
            
            save_user_bots()
        else:
            bot.send_message(user_id, error_message("Please upload a file document"), parse_mode='Markdown')
    except Exception as e:
        bot.send_message(user_id, error_message(f"File error: {str(e)}"), parse_mode='Markdown')

@bot.message_handler(commands=['run'])
def run_bot(message):
    user_id = str(message.from_user.id)
    if user_id not in user_bots or not user_bots[user_id]:
        bot.send_message(user_id, error_message("No bots available. Create one with /newbot"), parse_mode='Markdown')
        return
    
    bot_name = temp_data.get(user_id, {}).get('current_bot')
    if not bot_name:
        bot.send_message(user_id, error_message("Select a bot first using /listbots"), parse_mode='Markdown')
        return
    
    if user_id in running_bots and bot_name in running_bots[user_id]:
        bot.send_message(user_id, error_message("Bot is already running!"), parse_mode='Markdown')
        return
    
    try:
        main_file = user_bots[user_id][bot_name]['main_file']
        path = f"user_bots/{user_id}/{bot_name}/"
        
        def run_process():
            try:
                process = subprocess.Popen(['python', path + main_file])
                if user_id not in running_bots:
                    running_bots[user_id] = {}
                running_bots[user_id][bot_name] = True
                save_running_bots()
            except Exception as e:
                bot.send_message(user_id, error_message(f"Runtime error: {str(e)}"), parse_mode='Markdown')
        
        thread = threading.Thread(target=run_process)
        thread.start()
        
        status_msg = success_message(f"Bot '{bot_name}' started!") + "\n\n"
        status_msg += "📈 Status: Running\n"
        status_msg += f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(user_id, status_msg, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(user_id, error_message(f"Startup failed: {str(e)}"), parse_mode='Markdown')

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    user_id = str(message.from_user.id)
    if user_id not in user_bots or not user_bots[user_id]:
        bot.send_message(user_id, error_message("No bots to stop"), parse_mode='Markdown')
        return
    
    bot_name = temp_data.get(user_id, {}).get('current_bot')
    if not bot_name:
        bot.send_message(user_id, error_message("Select a bot first using /listbots"), parse_mode='Markdown')
        return
    
    if user_id in running_bots and bot_name in running_bots[user_id]:
        os.system(f"pkill -f 'python user_bots/{user_id}/{bot_name}/.*'")
        del running_bots[user_id][bot_name]
        save_running_bots()
        bot.send_message(user_id, success_message(f"Bot '{bot_name}' stopped!"), parse_mode='Markdown')
    else:
        bot.send_message(user_id, error_message("Bot wasn't running"), parse_mode='Markdown')

@bot.message_handler(commands=['restart'])
def handle_restart(message):
    user_id = str(message.from_user.id)
    args = message.text.split()[1:]
    
    if not args:
        bot.reply_to(message, error_message("Please specify a bot name.\nUsage: /restart <botname>"), parse_mode='Markdown')
        return
    
    bot_name = ' '.join(args)
    if user_id not in user_bots or bot_name not in user_bots[user_id]:
        bot.reply_to(message, error_message(f"Bot '{bot_name}' not found!"), parse_mode='Markdown')
        return
    
    try:
        # Stop if running
        if user_id in running_bots and bot_name in running_bots[user_id]:
            os.system(f"pkill -f 'python user_bots/{user_id}/{bot_name}/.*'")
            del running_bots[user_id][bot_name]
        
        # Start bot
        main_file = user_bots[user_id][bot_name]['main_file']
        path = f"user_bots/{user_id}/{bot_name}/"
        
        def run_process():
            process = subprocess.Popen(['python', path + main_file])
            if user_id not in running_bots:
                running_bots[user_id] = {}
            running_bots[user_id][bot_name] = True
            save_running_bots()
        
        threading.Thread(target=run_process).start()
        bot.reply_to(message, success_message(f"Bot '{bot_name}' restarted successfully!"), parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, error_message(f"Restart failed: {str(e)}"), parse_mode='Markdown')

@bot.message_handler(commands=['delete'])
def handle_delete(message):
    user_id = str(message.from_user.id)
    args = message.text.split()[1:]
    
    if not args:
        bot.reply_to(message, error_message("Please specify a bot name.\nUsage: /delete <botname>"), parse_mode='Markdown')
        return
    
    bot_name = ' '.join(args)
    if user_id not in user_bots or bot_name not in user_bots[user_id]:
        bot.reply_to(message, error_message(f"Bot '{bot_name}' not found!"), parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Confirm", callback_data=f"delete_confirm_{bot_name}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel")
    )
    bot.send_message(user_id, 
                   f"⚠️ *PERMANENT DELETION* ⚠️\nAre you sure you want to delete '{bot_name}'?\nAll files and data will be lost!",
                   reply_markup=markup,
                   parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_confirm_'))
def confirm_delete(call):
    user_id = str(call.from_user.id)
    bot_name = call.data.split('_')[2]
    
    try:
        # Stop bot if running
        if user_id in running_bots and bot_name in running_bots[user_id]:
            os.system(f"pkill -f 'python user_bots/{user_id}/{bot_name}/.*'")
            del running_bots[user_id][bot_name]
            save_running_bots()
        
        # Remove from user bots
        del user_bots[user_id][bot_name]
        if not user_bots[user_id]:
            del user_bots[user_id]
        save_user_bots()
        
        # Delete files
        dir_path = f"user_bots/{user_id}/{bot_name}"
        shutil.rmtree(dir_path, ignore_errors=True)
        
        bot.send_message(user_id, success_message(f"Bot '{bot_name}' permanently deleted!"), parse_mode='Markdown')
    except Exception as e:
        bot.send_message(user_id, error_message(f"Deletion failed: {str(e)}"), parse_mode='Markdown')
    finally:
        bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'delete_cancel')
def cancel_delete(call):
    user_id = str(call.from_user.id)
    bot.send_message(user_id, "🗑️ Deletion cancelled.")
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['status'])
def handle_status(message):
    user_id = str(message.from_user.id)
    args = message.text.split()[1:]
    
    if not args:
        bot.reply_to(message, error_message("Please specify a bot name.\nUsage: /status <botname>"), parse_mode='Markdown')
        return
    
    bot_name = ' '.join(args)
    if user_id not in user_bots or bot_name not in user_bots[user_id]:
        bot.reply_to(message, error_message(f"Bot '{bot_name}' not found!"), parse_mode='Markdown')
        return
    
    status = "🟢 RUNNING" if running_bots.get(user_id, {}).get(bot_name) else "🔴 STOPPED"
    info = user_bots[user_id][bot_name]
    response = f"📊 *{bot_name} Status*\n\n"
    response += f"📅 Created: `{datetime.fromisoformat(info['created']).strftime('%Y-%m-%d %H:%M')}`\n"
    response += f"📄 Main File: `{info['main_file']}`\n"
    response += f"🚦 Status: {status}"
    
    bot.send_message(user_id, response, parse_mode='Markdown')

@bot.message_handler(commands=['listbots'])
def list_bots(message):
    user_id = str(message.from_user.id)
    if user_id not in user_bots or not user_bots[user_id]:
        bot.send_message(user_id, error_message("You have no bots yet!"), parse_mode='Markdown')
        return
    
    markup = types.InlineKeyboardMarkup()
    for bot_name in user_bots[user_id]:
        status = "🟢" if running_bots.get(user_id, {}).get(bot_name) else "🔴"
        btn_text = f"{status} {bot_name}"
        markup.row(
            types.InlineKeyboardButton(btn_text, callback_data=f"select_{bot_name}"),
            types.InlineKeyboardButton("🗑️", callback_data=f"delete_{bot_name}")
        )
    
    bot.send_message(user_id, stylish_message("Your Bots:"), reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def select_bot(call):
    user_id = str(call.from_user.id)
    bot_name = call.data.split('_')[1]
    temp_data[user_id] = {'current_bot': bot_name}
    
    info = user_bots[user_id][bot_name]
    status = "🟢 Running" if running_bots.get(user_id, {}).get(bot_name) else "🔴 Stopped"
    
    response = stylish_message(f"Selected: {bot_name}") + "\n\n"
    response += f"📅 Created: {datetime.fromisoformat(info['created']).strftime('%Y-%m-%d')}\n"
    response += f"📄 Main file: `{info['main_file']}`\n"
    response += f"📈 Status: {status}"
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{bot_name}"),
        types.InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{bot_name}")
    )
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('restart_'))
def restart_bot(call):
    user_id = str(call.from_user.id)
    bot_name = call.data.split('_')[1]
    
    try:
        if user_id in running_bots and bot_name in running_bots[user_id]:
            os.system(f"pkill -f 'python user_bots/{user_id}/{bot_name}/.*'")
            del running_bots[user_id][bot_name]
        
        main_file = user_bots[user_id][bot_name]['main_file']
        path = f"user_bots/{user_id}/{bot_name}/"
        
        def run_process():
            process = subprocess.Popen(['python', path + main_file])
            if user_id not in running_bots:
                running_bots[user_id] = {}
            running_bots[user_id][bot_name] = True
            save_running_bots()
        
        threading.Thread(target=run_process).start()
        bot.answer_callback_query(call.id, "🔄 Restarting bot...")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot_callback(call):
    user_id = str(call.from_user.id)
    bot_name = call.data.split('_')[1]
    
    try:
        if user_id in running_bots and bot_name in running_bots[user_id]:
            os.system(f"pkill -f 'python user_bots/{user_id}/{bot_name}/.*'")
            del running_bots[user_id][bot_name]
            save_running_bots()
            bot.answer_callback_query(call.id, "⏹️ Bot stopped")
        else:
            bot.answer_callback_query(call.id, "❌ Bot not running")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

def restart_all_bots():
    for user_id, bots in running_bots.items():
        for bot_name in bots:
            try:
                path = f"user_bots/{user_id}/{bot_name}/"
                main_file = user_bots[user_id][bot_name]['main_file']
                subprocess.Popen(['python', path + main_file])
            except Exception as e:
                print(f"Restart error: {str(e)}")

if __name__ == '__main__':
    os.makedirs("user_bots", exist_ok=True)
    restart_all_bots()
    print("🤖 Host Bot is running...")
    bot.infinity_polling()