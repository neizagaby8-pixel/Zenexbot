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
        "AM": ("🇦🇲", "ARMENIA"), "BD": ("🇧🇩", "BANGLADESH"), "IN": ("🇮🇳", "INDIA"),
        "US": ("🇺🇸", "UNITED STATES"), "GB": ("🇬🇧", "UNITED KINGDOM"), "RU": ("🇷🇺", "RUSSIA"),
        "TJ": ("🇹🇯", "TAJIKISTAN"), "MG": ("🇲🇬", "MADAGASCAR"), "UA": ("🇺🇦", "UKRAINE"),
        "GN": ("🇬🇳", "GUINEA"), "TG": ("🇹🇬", "TOGO"), "CM": ("🇨🇲", "CAMEROON"),
        "CI": ("🇨🇮", "IVORY COAST"), "CF": ("🇨🇫", "CENTRAL AFRICAN REPUBLIC"), "BJ": ("🇧🇯", "BENIN"),
        "MY": ("🇲🇾", "MALAYSIA"), "MA": ("🇲🇦", "MOROCCO"), "SD": ("🇸🇩", "SUDAN"),
        "TZ": ("🇹🇿", "TANZANIA"), "ZW": ("🇿🇼", "ZIMBABWE"), "DZ": ("🇩🇿", "ALGERIA"),
        "BO": ("🇧🇴", "BOLIVIA"), "EG": ("🇪🇬", "EGYPT"), "GH": ("🇬🇭", "GHANA"),
        "BR": ("🇧🇷", "BRAZIL"), "PK": ("🇵🇰", "PAKISTAN"), "ID": ("🇮🇩", "INDONESIA"),
        "VN": ("🇻🇳", "VIETNAM"), "PH": ("🇵🇭", "PHILIPPINES"), "TR": ("🇹🇷", "TURKEY"),
        "IR": ("🇮🇷", "IRAN"), "NP": ("🇳🇵", "NEPAL"), "ME": ("🇲🇪", "MONTENEGRO"),
        "SL": ("🇸🇱", "SIERRA LEONE")
    }

    if len(c_field) == 2 and c_field in country_data:
        return country_data[c_field][0], c_field, country_data[c_field][1]
        
    prefix_to_iso = {
        "374": "AM", "880": "BD", "91": "IN", "1": "US", "44": "GB", "7": "RU", 
        "992": "TJ", "261": "MG", "380": "UA", "224": "GN", "228": "TG", 
        "237": "CM", "225": "CI", "236": "CF", "229": "BJ", "60": "MY", 
        "212": "MA
