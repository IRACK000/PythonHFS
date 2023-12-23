from fastapi_cache.decorator import cache
from pathlib import Path
import pyotp

try:
    from setting_local import setting as __setting
except ModuleNotFoundError as e:
    print(e, "Could not find setting.local.py. Please use localized settings file instead of default settings file.")
    from setting import setting as __setting


def __import_settings(setting: dict):
    root = Path(setting['root_dir'])
    setting['root_dir'] = root
    setting['guest_dir'] = root / setting['guest_dir']
    for _, info in setting['users'].items():
        info['home'] = root / info['home']
        info['otp_key'] = pyotp.TOTP(info['otp_key'])


__import_settings(__setting)
guest_directory = __setting['guest_dir']


@cache(expire=60*5)  # cache for five minutes
def check_user(username: str, password: str) -> Path:
    try:
        users = __setting['users']
        user = users[username]
        if password != user['password']+user['otp_key'].now():
            raise Exception
        return user['home']
    except Exception:
        raise ValueError("Invalid credentials")
