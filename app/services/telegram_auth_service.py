import hashlib
import hmac
import time


def verify_telegram_login(data, bot_token):
    if not bot_token:
        return False

    auth_date = data.get('auth_date')
    hash_value = data.get('hash')
    if not auth_date or not hash_value:
        return False

    try:
        auth_timestamp = int(auth_date)
    except ValueError:
        return False

    if auth_timestamp > time.time() + 300:
        return False
    if time.time() - auth_timestamp > 86400:
        return False

    check_data = [f'{key}={value}' for key, value in data.items() if key != 'hash']
    check_data.sort()
    data_check_string = '\n'.join(check_data)

    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash, hash_value)
