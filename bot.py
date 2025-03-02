import telebot
from telebot import types
import os
import json
import yt_dlp
from dotenv import load_dotenv
import requests

# .env থেকে ডাটা লোড
load_dotenv()
BOT_TOKEN = os.getenv('MAIN_BOT_TOKEN')
REPORT_BOT_TOKEN = os.getenv('REPORT_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')

# ফিচার অন/অফ সিস্টেম
ENABLE_GROUPS = os.getenv('ENABLE_GROUPS', 'True') == 'True'
ENABLE_QUALITY_SELECTION = os.getenv('ENABLE_QUALITY_SELECTION', 'True') == 'True'
ENABLE_AUDIO_VIDEO_SELECTION = os.getenv('ENABLE_AUDIO_VIDEO_SELECTION', 'True') == 'True'

# বট সেটআপ
bot = telebot.TeleBot(BOT_TOKEN)
report_bot = telebot.TeleBot(REPORT_BOT_TOKEN)

USER_DATA_FILE = "utils/user_data.json"

# ইউজার ডেটা লোড
def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

# ইউজার ডেটা সেভ
def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# কয়েন সিস্টেম
def update_user_coins(user_id, coins):
    data = load_user_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {"coins": 20, "referrals": 0}  # ওয়েলকাম বোনাস
    data[user_id]["coins"] += coins
    save_user_data(data)

def get_user_coins(user_id):
    data = load_user_data()
    return data.get(str(user_id), {}).get("coins", 0)

# চ্যানেল মেম্বারশিপ চেক
def is_user_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# গুগল এআই স্টুডিওর মাধ্যমে উত্তর আনা
def get_ai_response(message):
    url = "https://generativelanguage.googleapis.com/v1/models/chat-bison-001:generateText"
    headers = {"Content-Type": "application/json"}
    params = {"key": GOOGLE_AI_KEY}
    data = {"prompt": message, "max_tokens": 150}
    
    response = requests.post(url, headers=headers, params=params, json=data)
    if response.status_code == 200:
        return response.json().get("candidates", [{}])[0].get("output", "আমি বুঝতে পারিনি।")
    return "সার্ভারে সমস্যা হচ্ছে, পরে চেষ্টা করুন।"

# ভিডিও ডাউনলোড ফাংশন
def download_video(url, quality="best"):
    ydl_opts = {
        "format": quality,
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "noplaylist": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info_dict)
    return file_path

# 📌 /start কমান্ড
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    update_user_coins(user_id, 0)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎥 Download", "👤 My Account", "🎁 Daily Bonus", "📢 Refer")
    
    bot.send_message(message.chat.id, "👋 স্বাগতম! একটি অপশন নির্বাচন করুন:", reply_markup=markup)

# 🎥 Download অপশন
@bot.message_handler(func=lambda message: message.text == "🎥 Download")
def ask_for_link(message):
    bot.send_message(message.chat.id, "🔗 দয়া করে ভিডিও লিংক পাঠান:")

@bot.message_handler(func=lambda message: message.text.startswith("http"))
def process_link(message):
    user_id = message.from_user.id
    
    if not is_user_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔥 Join Now 🔥", url=f"https://t.me/{CHANNEL_ID}"))
        markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
        bot.send_message(message.chat.id, "🔔 দয়া করে আমাদের চ্যানেলে যোগ দিন!", reply_markup=markup)
        return
    
    if get_user_coins(user_id) < 5:
        bot.send_message(message.chat.id, "🚫 আপনার পর্যাপ্ত কয়েন নেই!")
        return
    
    url = message.text
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎥 Fast Download", callback_data=f"fast|{url}"))
    markup.add(types.InlineKeyboardButton("📥 Slow Download", callback_data=f"slow|{url}"))
    
    bot.send_message(message.chat.id, "🔽 কিভাবে ডাউনলোড করতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("fast") or call.data.startswith("slow"))
def download_callback(call):
    data = call.data.split("|")
    mode = data[0]
    url = data[1]
    
    bot.edit_message_text("⏳ ডাউনলোড হচ্ছে...", call.message.chat.id, call.message.message_id)
    
    try:
        file_path = download_video(url)
        
        if mode == "fast":
            bot.edit_message_text(f"✅ ডাউনলোড সম্পন্ন! 🔗 [ডাউনলোড লিংক]({file_path})", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "📤 আপলোড হচ্ছে...")
            bot.send_document(call.message.chat.id, open(file_path, "rb"))
        
        update_user_coins(call.from_user.id, -5)
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ ডাউনলোড ব্যর্থ! পরে চেষ্টা করুন।")
        report_bot.send_message(ADMIN_CHAT_ID, f"❗ ডাউনলোড ইরর:\n{str(e)}")

# ✅ চ্যানেল জয়েন কনফার্মেশন
@bot.callback_query_handler(func=lambda call: call.data == "joined")
def verify_join(call):
    if is_user_member(call.from_user.id):
        bot.edit_message_text("✅ চ্যানেল জয়েন কনফার্মড! এখন আপনি ডাউনলোড করতে পারেন।", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেল জয়েন করেননি!")

# 📌 সাধারণ মেসেজের উত্তর গুগল এআই স্টুডিও দিয়ে
@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    response = get_ai_response(message.text)
    bot.send_message(message.chat.id, response)

# বট চালু করা
bot.polling()
