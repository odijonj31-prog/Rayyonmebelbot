import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

_admin_ids_raw = os.getenv("SUPER_ADMIN_ID", "0")
SUPER_ADMIN_IDS = set(int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip())

DATABASE_URL = os.getenv("DATABASE_URL")

# Mini App joylashgan manzil (Railway domeni). Masalan: https://rayyonmebel.up.railway.app
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# AI narx maslahatchisi uchun
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Menejerning Telegram username'i (masalan: "odilbekl", @ belgisiz)
# Bo'sh qoldirilsa, "Menejerga yozish" tugmasi hozircha sozlanmagan deydi
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "")

# Web server port (Railway PORT o'zgaruvchisini avtomatik beradi)
PORT = int(os.getenv("PORT", "8080"))

COMPANY_NAME = "RAYYON Mebel"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylida topilmadi!")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL .env faylida topilmadi!")
