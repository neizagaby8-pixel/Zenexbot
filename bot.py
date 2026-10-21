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
