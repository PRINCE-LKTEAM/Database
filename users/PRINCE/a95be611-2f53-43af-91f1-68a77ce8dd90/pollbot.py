import telebot
from telebot import types
import time
import threading
import json
import os
from datetime import datetime, timedelta

# Initialize bot with your token
TOKEN = "7846267795:AAH9tiH5iQkxkpiUiURESbdpgI5xfGVrhik"
bot = telebot.TeleBot(TOKEN)

# Data storage
if not os.path.exists('polls_data.json'):
    with open('polls_data.json', 'w') as f:
        json.dump({}, f)

# Load existing polls data
def load_polls():
    with open('polls_data.json', 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Save polls data
def save_polls(polls_data):
    with open('polls_data.json', 'w') as f:
        json.dump(polls_data, f)

# Poll class to manage each poll
class Poll:
    def __init__(self, creator_id, question, options, anonymous=True, multiple_answers=False, duration_minutes=60):
        self.id = f"poll_{int(time.time())}_{creator_id}"
        self.creator_id = creator_id
        self.question = question
        self.options = options
        self.anonymous = anonymous
        self.multiple_answers = multiple_answers
        self.duration_minutes = duration_minutes
        self.end_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.votes = {option: [] for option in options}
        self.active = True
        self.messages = []  # List of message IDs where this poll is displayed

    def add_vote(self, user_id, user_name, option):
        if not self.active:
            return False, "This poll has ended."
        
        if not self.multiple_answers:
            # Remove previous votes by this user
            for opt in self.options:
                if user_id in [vote['id'] for vote in self.votes[opt]]:
                    self.votes[opt] = [vote for vote in self.votes[opt] if vote['id'] != user_id]
        
        # Add the new vote
        if option in self.options:
            # Check if user already voted for this option
            if user_id in [vote['id'] for vote in self.votes[option]]:
                return False, "You've already voted for this option."
            
            self.votes[option].append({'id': user_id, 'name': user_name})
            return True, "Your vote has been counted."
        
        return False, "Invalid option."

    def end_poll(self):
        self.active = False
        return self.get_results()

    def get_results(self):
        results = {}
        total_votes = sum(len(votes) for votes in self.votes.values())
        
        for option in self.options:
            vote_count = len(self.votes[option])
            percentage = (vote_count / total_votes) * 100 if total_votes > 0 else 0
            results[option] = {
                'count': vote_count,
                'percentage': round(percentage, 1),
                'voters': [vote['name'] for vote in self.votes[option]] if not self.anonymous else []
            }
        
        return results

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'question': self.question,
            'options': self.options,
            'anonymous': self.anonymous,
            'multiple_answers': self.multiple_answers,
            'duration_minutes': self.duration_minutes,
            'end_time': self.end_time.isoformat(),
            'votes': self.votes,
            'active': self.active,
            'messages': self.messages
        }

    @classmethod
    def from_dict(cls, data):
        poll = cls(
            data['creator_id'],
            data['question'],
            data['options'],
            data['anonymous'],
            data['multiple_answers'],
            data['duration_minutes']
        )
        poll.id = data['id']
        poll.votes = data['votes']
        poll.active = data['active']
        poll.end_time = datetime.fromisoformat(data['end_time'])
        poll.messages = data['messages']
        return poll

# Global state
polls = {}
user_states = {}  # To track user state during poll creation
temp_polls = {}   # To store polls during creation process

# Load existing polls
polls_data = load_polls()
for poll_id, poll_data in polls_data.items():
    polls[poll_id] = Poll.from_dict(poll_data)

# Helper functions
def is_admin(user_id, chat_id):
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

def create_poll_keyboard(poll_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    poll = polls[poll_id]
    
    for option in poll.options:
        # Show vote count for each option
        vote_count = len(poll.votes[option])
        btn_text = f"{option} ({vote_count} votes)"
        callback_data = f"vote:{poll_id}:{option}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    # Add control buttons
    buttons_row = []
    
    # Add "End Poll" button for creator
    buttons_row.append(types.InlineKeyboardButton("End Poll 🛑", callback_data=f"end:{poll_id}"))
    
    # Add "Share Poll" button
    if poll.active:
        buttons_row.append(types.InlineKeyboardButton("Share Poll 🔄", callback_data=f"share:{poll_id}"))
    
    markup.row(*buttons_row)
    return markup

def create_poll_message(poll_id):
    poll = polls[poll_id]
    status = "Active" if poll.active else "Ended"
    anonymous_status = "Anonymous" if poll.anonymous else "Public"
    multiple_status = "Multiple answers allowed" if poll.multiple_answers else "Single answer only"
    
    message = f"📊 *POLL: {poll.question}*\n\n"
    message += f"• Status: {status}\n"
    message += f"• Voting: {anonymous_status}\n"
    message += f"• Type: {multiple_status}\n"
    message += f"• Ends: {poll.end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if not poll.active:
        results = poll.get_results()
        message += "*Results:*\n"
        for option in poll.options:
            res = results[option]
            message += f"• {option}: {res['count']} votes ({res['percentage']}%)\n"
            if not poll.anonymous and res['voters']:
                message += f"  _Voters: {', '.join(res['voters'][:5])}"
                if len(res['voters']) > 5:
                    message += f" and {len(res['voters']) - 5} more_\n"
                else:
                    message += "_\n"
    else:
        message += "Click an option below to vote!"
    
    return message

# Bot commands
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
                "Welcome to the Poll Bot! 📊\n\n"
                "Commands:\n"
                "/newpoll - Create a new poll\n"
                "/help - Show help information")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "*Poll Bot Help*\n\n"
        "*Commands:*\n"
        "• /newpoll - Start creating a new poll\n"
        "• /cancel - Cancel current operation\n"
        "• /help - Show this help message\n\n"
        
        "*Features:*\n"
        "• Create polls with multiple options\n"
        "• Set anonymous or public voting\n"
        "• Allow single or multiple answers\n"
        "• Set poll duration\n"
        "• Share polls to groups and channels\n"
        "• Only admins can create polls in groups\n\n"
        
        "*Creating a Poll:*\n"
        "1. Use /newpoll to start\n"
        "2. Enter your question\n"
        "3. Add options (one per message)\n"
        "4. Configure poll settings\n"
        "5. Publish your poll\n"
        "6. Optionally share your poll to other chats\n\n"
        
        "Enjoy polling! 📊"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['newpoll'])
def new_poll(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if in a group and user is admin
    if message.chat.type in ['group', 'supergroup']:
        if not is_admin(user_id, chat_id):
            bot.reply_to(message, "Only admins can create polls in this group.")
            return
    
    # Initialize poll creation state
    user_states[user_id] = {
        'state': 'waiting_question',
        'chat_id': chat_id
    }
    
    bot.send_message(chat_id, "Let's create a new poll! 📊\n\nPlease enter the poll question:")

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    user_id = message.from_user.id
    
    if user_id in user_states:
        del user_states[user_id]
        if user_id in temp_polls:
            del temp_polls[user_id]
        bot.send_message(message.chat.id, "Operation cancelled.")
    else:
        bot.send_message(message.chat.id, "No active operation to cancel.")

# Handle poll creation flow
@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def poll_creation_flow(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    state = user_states[user_id]['state']
    
    if state == 'waiting_question':
        # Save the question
        temp_polls[user_id] = {
            'question': text,
            'options': [],
        }
        user_states[user_id]['state'] = 'waiting_options'
        bot.send_message(chat_id, 
                        f"Question: *{text}*\n\n"
                        "Now, send me the answer options one by one.\n"
                        "Type /done when you've added all options.", 
                        parse_mode='Markdown')
    
    elif state == 'waiting_options':
        if text == '/done':
            if len(temp_polls[user_id]['options']) < 2:
                bot.send_message(chat_id, "You need at least 2 options for a poll. Please add more options.")
                return
                
            # Move to poll settings
            user_states[user_id]['state'] = 'waiting_settings'
            
            # Create settings keyboard
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("Anonymous: YES", callback_data="set:anonymous:yes"),
                types.InlineKeyboardButton("Multiple answers: NO", callback_data="set:multiple:no")
            )
            
            # Duration buttons
            markup.add(
                types.InlineKeyboardButton("15 min", callback_data="set:duration:15"),
                types.InlineKeyboardButton("30 min", callback_data="set:duration:30"),
                types.InlineKeyboardButton("1 hour", callback_data="set:duration:60"),
                types.InlineKeyboardButton("6 hours", callback_data="set:duration:360")
            )
            
            # Create poll button
            markup.add(types.InlineKeyboardButton("CREATE POLL", callback_data="create_poll"))
            
            # Add current settings to temp_polls
            temp_polls[user_id]['anonymous'] = True
            temp_polls[user_id]['multiple_answers'] = False
            temp_polls[user_id]['duration_minutes'] = 60
            
            # Display options and settings
            options_text = "\n".join([f"• {opt}" for opt in temp_polls[user_id]['options']])
            bot.send_message(chat_id, 
                            f"*Poll Preview*\n\n"
                            f"*Question:* {temp_polls[user_id]['question']}\n\n"
                            f"*Options:*\n{options_text}\n\n"
                            f"Now, configure your poll settings:",
                            reply_markup=markup, 
                            parse_mode='Markdown')
        else:
            # Add option to the list
            temp_polls[user_id]['options'].append(text)
            bot.send_message(chat_id, 
                            f"Added option: *{text}*\n"
                            f"({len(temp_polls[user_id]['options'])} options so far)\n\n"
                            "Send another option or type /done when finished.",
                            parse_mode='Markdown')
    
    elif state == 'waiting_share_to':
        # This state is for handling poll sharing
        poll_id = user_states[user_id].get('sharing_poll_id')
        if poll_id and poll_id in polls:
            try:
                # Try to find the chat by username/ID
                target_chat = None
                try:
                    # First try as a chat ID
                    chat_id_to_try = int(text) if text.strip('-').isdigit() else None
                    if chat_id_to_try:
                        target_chat = bot.get_chat(chat_id_to_try)
                except:
                    pass
                
                if not target_chat:
                    # Try as a username
                    try:
                        username = text.strip('@')
                        target_chat = bot.get_chat(f"@{username}")
                    except:
                        bot.send_message(chat_id, 
                                        "I couldn't find that chat. Make sure:\n"
                                        "1. The bot is a member of the target group/channel\n"
                                        "2. You entered a valid username (@username) or chat ID\n\n"
                                        "Try again or type /cancel to abort.")
                        return
                
                # Send the poll to the target chat
                keyboard = create_poll_keyboard(poll_id)
                poll_message = create_poll_message(poll_id)
                
                sent_message = bot.send_message(
                    chat_id=target_chat.id,
                    text=poll_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                # Store the message ID
                polls[poll_id].messages.append({
                    'chat_id': target_chat.id,
                    'message_id': sent_message.message_id
                })
                
                # Save polls data
                save_polls({poll_id: poll.to_dict() for poll_id, poll in polls.items()})
                
                # Clear user state
                del user_states[user_id]
                
                bot.send_message(chat_id, 
                                f"✅ Poll successfully shared to {target_chat.title if hasattr(target_chat, 'title') else target_chat.username}!")
                
            except Exception as e:
                bot.send_message(chat_id, 
                                f"❌ Error sharing poll: {str(e)}\n\n"
                                "Make sure the bot is added to the target chat and has permission to send messages there.")
                print(f"Error sharing poll: {e}")
                
                # Clear user state
                del user_states[user_id]

# Handle callback queries (button clicks)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Poll settings callbacks
    if call.data.startswith('set:'):
        if user_id in user_states and user_states[user_id]['state'] == 'waiting_settings':
            _, setting, value = call.data.split(':')
            
            if setting == 'anonymous':
                temp_polls[user_id]['anonymous'] = value == 'yes'
                new_text = "Anonymous: YES" if value == 'yes' else "Anonymous: NO"
                new_value = 'no' if value == 'yes' else 'yes'
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=update_keyboard(call.message.reply_markup, f"set:anonymous:{value}", f"set:anonymous:{new_value}", new_text)
                )
            
            elif setting == 'multiple':
                temp_polls[user_id]['multiple_answers'] = value == 'yes'
                new_text = "Multiple answers: YES" if value == 'yes' else "Multiple answers: NO"
                new_value = 'no' if value == 'yes' else 'yes'
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=update_keyboard(call.message.reply_markup, f"set:multiple:{value}", f"set:multiple:{new_value}", new_text)
                )
            
            elif setting == 'duration':
                temp_polls[user_id]['duration_minutes'] = int(value)
                bot.answer_callback_query(call.id, f"Poll duration set to {value} minutes")
            
            bot.answer_callback_query(call.id)
    
    # Create poll callback
    elif call.data == 'create_poll':
        if user_id in user_states and user_id in temp_polls:
            poll_data = temp_polls[user_id]
            
            # Create a new poll
            new_poll = Poll(
                user_id,
                poll_data['question'],
                poll_data['options'],
                poll_data['anonymous'],
                poll_data['multiple_answers'],
                poll_data['duration_minutes']
            )
            
            # Save the poll
            polls[new_poll.id] = new_poll
            
            # Create the poll message
            keyboard = create_poll_keyboard(new_poll.id)
            poll_message = create_poll_message(new_poll.id)
            
            # Send the poll
            sent_message = bot.send_message(
                chat_id=chat_id,
                text=poll_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            # Store the message ID
            new_poll.messages.append({
                'chat_id': chat_id,
                'message_id': sent_message.message_id
            })
            
            # Start the poll timer
            setup_poll_timer(new_poll.id)
            
            # Save polls data
            save_polls({poll_id: poll.to_dict() for poll_id, poll in polls.items()})
            
            # Clear user state
            del user_states[user_id]
            del temp_polls[user_id]
            
            bot.answer_callback_query(call.id, "Poll created successfully!")
            
            # Edit the settings message to show that poll was created
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"✅ Poll created!\n\nQuestion: {poll_data['question']}\n\nThe poll is now active and will run for {poll_data['duration_minutes']} minutes."
            )
    
    # Vote callback
    elif call.data.startswith('vote:'):
        _, poll_id, option = call.data.split(':', 2)  # Split by max 2 to handle options with colons
        
        if poll_id in polls:
            poll = polls[poll_id]
            
            # Check if poll is still active
            if not poll.active:
                bot.answer_callback_query(call.id, "This poll has ended.")
                return
            
            # Record the vote
            user_name = call.from_user.first_name
            if call.from_user.last_name:
                user_name += f" {call.from_user.last_name}"
                
            success, message = poll.add_vote(user_id, user_name, option)
            
            # Update the poll message
            for msg in poll.messages:
                try:
                    bot.edit_message_text(
                        chat_id=msg['chat_id'],
                        message_id=msg['message_id'],
                        text=create_poll_message(poll_id),
                        reply_markup=create_poll_keyboard(poll_id),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Error updating poll message: {e}")
            
            # Save polls data
            save_polls({poll_id: poll.to_dict() for poll_id, poll in polls.items()})
            
            # Notify the user
            bot.answer_callback_query(call.id, message)
    
    # End poll callback
    elif call.data.startswith('end:'):
        _, poll_id = call.data.split(':')
        
        if poll_id in polls:
            poll = polls[poll_id]
            
            # Only creator or admins can end the poll
            if user_id == poll.creator_id or is_admin(user_id, chat_id):
                poll.end_poll()
                
                # Update all poll messages
                for msg in poll.messages:
                    try:
                        bot.edit_message_text(
                            chat_id=msg['chat_id'],
                            message_id=msg['message_id'],
                            text=create_poll_message(poll_id),
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"Error updating poll message: {e}")
                
                # Save polls data
                save_polls({poll_id: poll.to_dict() for poll_id, poll in polls.items()})
                
                bot.answer_callback_query(call.id, "Poll ended. Results are now available.")
            else:
                bot.answer_callback_query(call.id, "Only the poll creator or admins can end this poll.")
        else:
            bot.answer_callback_query(call.id, "Poll not found.")
    
    # Share poll callback
    elif call.data.startswith('share:'):
        _, poll_id = call.data.split(':')
        
        if poll_id in polls:
            poll = polls[poll_id]
            
            # Only creator or admins can share the poll
            if user_id == poll.creator_id or is_admin(user_id, chat_id):
                # Set up the sharing state
                user_states[user_id] = {
                    'state': 'waiting_share_to',
                    'sharing_poll_id': poll_id,
                    'chat_id': chat_id
                }
                
                bot.send_message(
                    chat_id=chat_id,
                    text="Where would you like to share this poll?\n\n"
                         "Please send me the username (e.g., @groupname) or ID of the group/channel. "
                         "Make sure I'm a member of that chat with permission to send messages.",
                    reply_markup=types.ForceReply(selective=True)
                )
                
                bot.answer_callback_query(call.id)
            else:
                bot.answer_callback_query(call.id, "Only the poll creator or admins can share this poll.")
        else:
            bot.answer_callback_query(call.id, "Poll not found.")

# Helper function to update keyboard
def update_keyboard(markup, old_data, new_data, new_text):
    new_markup = types.InlineKeyboardMarkup(row_width=markup.row_width)
    
    for row in markup.keyboard:
        new_row = []
        for button in row:
            if button.callback_data == old_data:
                new_row.append(types.InlineKeyboardButton(new_text, callback_data=new_data))
            else:
                new_row.append(button)
        new_markup.row(*new_row)
    
    return new_markup

# Poll timer setup
def setup_poll_timer(poll_id):
    poll = polls[poll_id]
    time_remaining = (poll.end_time - datetime.now()).total_seconds()
    
    if time_remaining > 0:
        # Schedule the poll to end
        timer = threading.Timer(time_remaining, end_poll_timer, args=[poll_id])
        timer.daemon = True
        timer.start()

def end_poll_timer(poll_id):
    if poll_id in polls:
        poll = polls[poll_id]
        
        if poll.active:
            poll.end_poll()
            
            # Update all poll messages
            for msg in poll.messages:
                try:
                    bot.edit_message_text(
                        chat_id=msg['chat_id'],
                        message_id=msg['message_id'],
                        text=create_poll_message(poll_id),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Error updating poll message: {e}")
            
            # Save polls data
            save_polls({poll_id: poll.to_dict() for poll_id, poll in polls.items()})
            
            print(f"Poll {poll_id} ended automatically.")

# Load and setup timers for existing active polls
def setup_existing_poll_timers():
    for poll_id, poll in polls.items():
        if poll.active:
            time_remaining = (poll.end_time - datetime.now()).total_seconds()
            if time_remaining > 0:
                timer = threading.Timer(time_remaining, end_poll_timer, args=[poll_id])
                timer.daemon = True
                timer.start()
            else:
                # Poll should have ended already
                end_poll_timer(poll_id)

# Main polling loop
if __name__ == "__main__":
    # Setup timers for existing polls
    setup_existing_poll_timers()
    
    # Start the bot
    print("Bot started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)