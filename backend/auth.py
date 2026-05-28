import hashlib
import secrets
from itsdangerous import URLSafeSerializer
import os

# Secret key for signing sessions
SECRET_KEY = os.getenv("SECRET_KEY", "aura_photography_super_secret_key_123456")
serializer = URLSafeSerializer(SECRET_KEY)

def hash_password(password: str) -> str:
    # Generate a random 16-byte salt
    salt = secrets.token_hex(16)
    # Derive key
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # Number of iterations
    )
    # Return formatted hash: algorithm$iterations$salt$key
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = parts[2]
        stored_key = parts[3]
        
        # Hash plain password with same salt and iterations
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return secrets.compare_digest(key.hex(), stored_key)
    except Exception:
        return False

def create_session_token(username: str) -> str:
    return serializer.dumps({"username": username})

def verify_session_token(token: str) -> str | None:
    try:
        data = serializer.loads(token)
        return data.get("username")
    except Exception:
        return None
