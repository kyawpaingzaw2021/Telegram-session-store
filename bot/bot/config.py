import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "6802169124").split(",")]
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID", 0))
KPAY_NUMBER = os.getenv("KPAY_NUMBER", "09255477757")
WAVE_NUMBER = os.getenv("WAVE_NUMBER", "09255477757")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

# ✅ Referral Bonus (ပြောင်းပြီး)
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", 5))

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
