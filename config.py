import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))

INITIATIVE_UUID = os.getenv("INITIATIVE_UUID", "49912c4c-d184-4112-81b4-9a809d841845")
INITIATIVE_PUB_ID = os.getenv("INITIATIVE_PUB_ID", "055521975013")
INITIATIVE_URL = f"https://openbudget.uz/boards/initiatives/initiative/55/{INITIATIVE_UUID}"

API_BASE = "https://openbudget.uz/api"
CAPTCHA_URL = f"{API_BASE}/v2/vote/captcha-2"
SEND_OTP_URL = f"{API_BASE}/v1/login/send-otp"
VERIFY_OTP_URL = f"{API_BASE}/v1/login/verify-otp"
INITIATIVE_URL_API = f"{API_BASE}/v1/initiatives/{INITIATIVE_UUID}"
FILE_URL = f"{API_BASE}/v2/info/file"

VOTING_START = os.getenv("VOTING_START", "2026-08-22")
VOTING_END = os.getenv("VOTING_END", "2026-08-31")
REWARD_AMOUNT = int(os.getenv("REWARD_AMOUNT", "15000"))

VOTE_CANDIDATES = [
    f"{API_BASE}/v2/vote/add",
    f"{API_BASE}/v1/vote/add",
    f"{API_BASE}/v2/vote",
    f"{API_BASE}/v1/vote",
    f"{API_BASE}/v2/initiatives/{INITIATIVE_UUID}/vote",
    f"{API_BASE}/v1/initiatives/{INITIATIVE_UUID}/vote",
    f"{API_BASE}/v2/boards/initiatives/vote",
    f"{API_BASE}/v1/boards/initiatives/vote",
]
