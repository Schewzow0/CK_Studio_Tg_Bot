import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")

ADMINS = list(map(int, os.getenv("ADMINS").split(",")))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

DB_PATH = os.getenv("DB_PATH", "database/CK_Studio_DB.db")
