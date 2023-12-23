from cachetools import cached,  TTLCache
from pathlib import Path
import pyotp

try:
    from .setting_local import setting as __setting
except ModuleNotFoundError as e:
    print(e, "Could not find setting.local.py. Please use localized settings file instead of default settings file.")
    from .setting import setting as __setting


def __import_settings(setting: dict):
    root = Path(setting['root_dir'])
    setting['root_dir'] = root
    setting['guest_dir'] = root / setting['guest_dir']
    for _, info in setting['users'].items():
        info['home'] = root / info['home']
        info['otp_key'] = pyotp.TOTP(info['otp_key'])


__import_settings(__setting)
guest_directory = __setting['guest_dir']


@cached(cache=TTLCache(maxsize=128, ttl=60*10))  # cache for five minutes
def check_user(username: str, password: str) -> Path:
    try:
        users = __setting['users']
        user = users[username]
        if password != user['password']+user['otp_key'].now():
            raise Exception
        return user['home']
    except Exception:
        raise ValueError("Invalid credentials")
