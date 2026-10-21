import logging
import requests
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = "8998738234:AAGpV1zS4miYRC9AxNpSHvJNyWPgkfI9-U4"
ADMIN_CHAT_ID = 6470943912  
OTP_GROUP_CHAT_ID = -1003857083035  

PANEL_API_KEY = "MTPXMVWZJWL"
BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api"

sent_otps_cache = set()
number_to_user_map = {}
user_target_ranges = {}
user_target_services = {}
waiting_for_range = {}
all_bot_users = set()

def extract_pure_code(full_text):
    text = str(full_text).strip()
    match = re.search(r'\b\d{4,8}\b', text)
    if match:
        return match.group(0)
    return text

def get_clean_digits(val):
    return re.sub(r'\D', '', str(val))

def get_country_info_by_range_or_text(range_str, country_field):
    c_field = str(country_field).strip().upper()
    r_str = get_clean_digits(range_str)
    
    country_data = {
        "AM": ("🇦🇲", "ARMENIA"),
        "BD": ("🇧🇩", "BANGLADESH"),
        "IN": ("🇮🇳", "INDIA"),
        "US": ("🇺🇸", "UNITED STATES"),
        "GB": ("🇬🇧", "UNITED KINGDOM"),
        "RU": ("🇷🇺", "RUSSIA"),
        "TJ": ("🇹🇯", "TAJIKISTAN"),
        "MG": ("🇲🇬", "MADAGASCAR"),
        "UA": ("🇺🇦", "UKRAINE"),
        "GN": ("🇬🇳", "GUINEA"),
        "TG": ("🇹🇬", "TOGO"),
        "CM": ("🇨🇲", "CAMEROON"),
        "CI": ("🇨🇮", "IVORY COAST"),
        "CF": ("🇨🇫", "CENTRAL AFRICAN REPUBLIC"),
        "BJ": ("🇧🇯", "BENIN"),
        "MY": ("🇲🇾", "MALAYSIA"),
        "MA": ("🇲🇦", "MOROCCO"),
        "SD": ("🇸🇩", "SUDAN"),
        "TZ": ("🇹🇿", "TANZANIA"),
        "ZW": ("🇿🇼", "ZIMBABWE"),
        "DZ": ("🇩🇿", "ALGERIA"),
        "BO": ("🇧🇴", "BOLIVIA"),
        "EG": ("🇪🇬", "EGYPT"),
        "GH": ("🇬🇭", "GHANA"),
        "BR": ("🇧🇷", "BRAZIL"),
        "PK": ("🇵🇰", "PAKISTAN"),
        "ID": ("🇮🇩", "INDONESIA"),
        "VN": ("🇻🇳", "VIETNAM"),
        "PH": ("🇵🇭", "PHILIPPINES"),
        "TR": ("🇹🇷", "TURKEY"),
        "IR": ("🇮🇷", "IRAN"),
        "NP": ("🇳🇵", "NEPAL"),
        "ME": ("🇲🇪", "MONTENEGRO"),
        "SL": ("🇸🇱", "SIERRA LEONE")
    }

    if len(c_field) == 2 and c_field in country_data:
        return country_data[c_field][0], c_field, country_data[c_field][1]
        
    prefix_to_iso = {
        "374": "AM", "880": "BD", "91": "IN", "1": "US", "44": "GB", "7": "RU", 
        "992": "TJ", "261": "MG", "380": "UA", "224": "GN", "228": "TG", 
        "237": "CM", "225": "CI", "236": "CF", "229": "BJ", "60": "MY", 
        "212": "MA", "249": "SD", "255": "TZ", "263": "ZW", "213": "DZ", 
        "591": "BO", "20": "EG", "233": "GH", "55": "BR", "92": "PK",
        "62": "ID", "84": "VN", "63": "PH", "90": "TR", "98": "IR", "977": "NP",
        "382": "ME", "232": "SL"
    }
    
    for prefix, iso in sorted(prefix_to_iso.items(), key=lambda x: len(x[0]), reverse=True):
        if r_str.startswith(prefix):
            if iso in country_data:
                return country_data[iso][0], iso, country_data[iso][1]

    return "🌍", c_field if c_field else "INT", "INTERNATIONAL"

async def auto_otp_checker(context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(f'{BASE_URL}/success-otp', headers={'mauthapi': PANEL_API_KEY}, timeout=5)
        res1 = res.json()
        if res1.get('meta', {}).get('code') == 200:
            otps_list = res1.get('data', {}).get('otps', [])
            
            for item in otps_list:
                raw_num = str(item.get('number', '')).strip()
                clean_num = get_clean_digits(raw_num)
                
                if not clean_num or clean_num not in number_to_user_map:
                    continue
                
                target_chat_id = number_to_user_map[clean_num]
                raw_msg = str(item.get('message', '')).strip()
                otp_text = extract_pure_code(raw_msg)
                
                otp_id = str(item.get('otp_id', '')).strip()
                unique_signature = f"id_{otp_id}" if otp_id else f"num_{clean_num}_otp_{otp_text}"
                
                if unique_signature in sent_otps_cache:
                    continue
                
                sent_otps_cache.add(unique_signature)
                if len(sent_otps_cache) > 1000:
                    sent_otps_cache.pop()
                    
                flag, c_code, _ = get_country_info_by_range_or_text(clean_num, "")
                selected_service = user_target_services.get(target_chat_id, "FACEBOOK")
                
                user_msg_text = (
                    f"🔔 **NEW VERIFICATION CODE RECEIVED**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 Country: {flag} `{c_code}`\n"
                    f"📱 Number: `+{clean_num}`\n"
                    f"📌 Service: 📘 `{selected_service}`\n"
                    f"🔑 OTP Code: `{otp_text}`\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ *Status: Successfully Delivered*"
                )
                
                if len(clean_num) >= 8:
                    prefix_part = clean_num[:5] 
                    suffix_part = clean_num[-4:] 
                    masked_num = f"{prefix_part}**{suffix_part}"
                else:
                    masked_num = clean_num[:2] + "**" + clean_num[-2:]
                
                group_msg_text = (
                    f"{flag} **{c_code}** | 📘 `{masked_num}` ➔ 🔑 `{otp_text}`"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("📢 Channel", url="https://t.me/your_channel_link"),
                        InlineKeyboardButton(f"🔑 {otp_text}", callback_data="noop")
                    ],
                    [InlineKeyboardButton("📞 Get Number", url="https://t.me/personal40bot")]
                ]
                group_reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await context.bot.send_message(chat_id=target_chat_id, text=user_msg_text, parse_mode="Markdown")
                except Exception as e:
                    print(f"Failed to send user message: {e}")
                
                try:
                    await context.bot.send_message(
                        chat_id=OTP_GROUP_CHAT_ID, 
                        text=group_msg_text, 
                        parse_mode="Markdown", 
                        reply_markup=group_reply_markup
                    )
                except Exception as e:
                    print(f"Failed to send group message: {e}")
    except Exception as e:
        print(f"Checker Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    all_bot_users.add(chat_id)

    keyboard = [
        [KeyboardButton("📞 Get API Number"), KeyboardButton("⚙️ Set Range")],
        [KeyboardButton("📱 Get Number"), KeyboardButton("🛠️ Select Service")],
        [KeyboardButton("📊 Live Traffic"), KeyboardButton("📩 Live OTP Inbox")],
        [KeyboardButton("👤 Account Profile")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = (
        f"👋 **Welcome to Automated OTP Gateway!**\n\n"
        f"✨ Fast, secure, and reliable virtual number & OTP management service.\n"
        f"📌 Please choose an option from the menu below to get started:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip
