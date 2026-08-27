import os
import re
import logging
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from bot.config import API_ID, API_HASH

logger = logging.getLogger(__name__)

_client_cache = {}

async def get_cached_client(session_path):
    if session_path in _client_cache:
        client = _client_cache[session_path]
        if client.is_connected() and await client.is_user_authorized():
            return client
        else:
            del _client_cache[session_path]
    if not os.path.exists(session_path):
        return None
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    _client_cache[session_path] = client
    return client

async def fetch_otp_from_777000(session_path: str) -> str | None:
    if not session_path or not os.path.exists(session_path):
        return None
    if not API_ID or not API_HASH:
        return None
    try:
        client = await get_cached_client(session_path)
        if not client:
            return None
        posts = await client(GetHistoryRequest(peer=777000, limit=1, offset_date=None,
                                               offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        kdotp = None
        if posts.messages:
            matches = re.findall(r'([\d.]*\d+)', posts.messages[0].message)
            if matches:
                if isinstance(matches[0], tuple):
                    kdotp = matches[0][0]
                else:
                    kdotp = matches[0]
        if not kdotp or len(kdotp) < 5:
            posts = await client(GetHistoryRequest(peer=777000, limit=2, offset_date=None,
                                                   offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for msg in posts.messages:
                if not msg.message:
                    continue
                matches = re.findall(r'([\d.]*\d+)', msg.message)
                if matches:
                    if isinstance(matches[0], tuple):
                        code = matches[0][0]
                    else:
                        code = matches[0]
                    if len(code) > 5:
                        kdotp = code
                        break
        if kdotp and len(kdotp) >= 4:
            return kdotp
        return None
    except Exception as e:
        logger.error(f"OTP Fetch Error: {e}")
        return None

async def check_session_health(session_path: str) -> bool:
    if not session_path or not os.path.exists(session_path):
        return False
    try:
        client = await get_cached_client(session_path)
        if not client:
            return False
        me = await client.get_me()
        return bool(me)
    except Exception:
        return False

async def check_new_login_from_777000(session_path: str, phone_number: str) -> bool:
    if not session_path or not os.path.exists(session_path):
        return False
    try:
        client = await get_cached_client(session_path)
        if not client:
            return False
        posts = await client(GetHistoryRequest(peer=777000, limit=2, offset_date=None,
                                               offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        clean_phone = phone_number.replace('+', '').replace(' ', '').strip()
        phone_suffix = clean_phone[-9:] if len(clean_phone) >= 9 else clean_phone
        for msg in posts.messages:
            if not msg.message:
                continue
            if "New login" in msg.message or "new login" in msg.message.lower():
                if phone_suffix in msg.message or clean_phone in msg.message:
                    return True
        return False
    except Exception as e:
        logger.error(f"New login check error: {e}")
        return False
