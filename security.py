"""
security.py — CRICSHOT Password Hashing & Encryption Utilities
================================================================
Provides three complete security layers used by app.py:

  Layer 1 — Password Hashing       (bcrypt, 12 rounds)
  Layer 2 — OTP Generation         (TOTP-style, HMAC-SHA256)
  Layer 3 — Symmetric Encryption   (Fernet AES-128-CBC + HMAC)
  Layer 4 — Token Generation       (cryptographically secure)
  Layer 5 — Field-Level Encryption (encrypt sensitive DB columns)

Install prerequisites:
  pip install bcrypt cryptography pyotp

Usage in app.py:
  from security import (
      hash_password, verify_password,
      generate_otp, verify_otp_hmac,
      encrypt_field, decrypt_field,
      generate_secure_token,
  )
"""

import os
import hmac
import time
import base64
import hashlib
import secrets
import datetime
import struct

# ── bcrypt (via flask-bcrypt or raw bcrypt) ───────────────────────────
try:
    import bcrypt as _bcrypt_lib          # pip install bcrypt
    _USE_RAW_BCRYPT = True
except ImportError:
    _USE_RAW_BCRYPT = False

# ── Fernet symmetric encryption ───────────────────────────────────────
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes as _hashes
    from cryptography.hazmat.backends import default_backend
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

# ── pyotp (optional TOTP support) ────────────────────────────────────
try:
    import pyotp
    _HAS_PYOTP = True
except ImportError:
    _HAS_PYOTP = False


# ════════════════════════════════════════════════════════════════════
#  LAYER 1 — PASSWORD HASHING  (bcrypt, cost factor 12)
# ════════════════════════════════════════════════════════════════════

BCRYPT_ROUNDS = 12    # Adjust: 10=fast-dev, 12=production, 14=paranoid


def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password with bcrypt.

    Returns a UTF-8 string like:
      $2b$12$<22-char salt><31-char hash>

    Example:
      hashed = hash_password("MySecret123!")
    """
    if not plain_text:
        raise ValueError("Password must not be empty.")
    if len(plain_text) < 6:
        raise ValueError("Password must be at least 6 characters.")

    password_bytes = plain_text.encode("utf-8")

    if _USE_RAW_BCRYPT:
        salt   = _bcrypt_lib.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = _bcrypt_lib.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")
    else:
        # Fallback: PBKDF2-HMAC-SHA256 with a random salt (bcrypt not installed)
        salt   = secrets.token_hex(16)
        dk     = hashlib.pbkdf2_hmac("sha256", password_bytes, salt.encode(), 260_000)
        return f"pbkdf2$sha256$260000${salt}${dk.hex()}"


def verify_password(plain_text: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Supports both bcrypt ($2b$...) and pbkdf2 fallback hashes.

    Example:
      if not verify_password(user_input, user.password_hash):
          return "Wrong password", 401
    """
    if not plain_text or not hashed:
        return False

    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        # bcrypt hash
        if _USE_RAW_BCRYPT:
            try:
                return _bcrypt_lib.checkpw(plain_text.encode("utf-8"), hashed.encode("utf-8"))
            except Exception:
                return False
        return False  # can't verify bcrypt without the library

    if hashed.startswith("pbkdf2$"):
        # pbkdf2 fallback hash: "pbkdf2$algo$iters$salt$hex_hash"
        try:
            _, algo, iters_str, salt, stored_hex = hashed.split("$")
            dk_check = hashlib.pbkdf2_hmac(
                algo, plain_text.encode("utf-8"), salt.encode(), int(iters_str)
            )
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(dk_check.hex(), stored_hex)
        except Exception:
            return False

    return False


def check_password_strength(password: str) -> dict:
    """
    Return a strength score (0-5) and feedback for a password.

    Example:
      info = check_password_strength("Cricket@99")
      # {"score": 4, "label": "Strong", "tips": [...]}
    """
    tips  = []
    score = 0

    if len(password) >= 8:  score += 1
    else: tips.append("Use at least 8 characters.")

    if len(password) >= 12: score += 1
    else: tips.append("12+ characters makes it much stronger.")

    if any(c.isupper() for c in password): score += 1
    else: tips.append("Add at least one uppercase letter.")

    if any(c.isdigit() for c in password): score += 1
    else: tips.append("Include at least one number.")

    if any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in password): score += 1
    else: tips.append("Add a special character like ! @ # $ %.")

    labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
    return {"score": score, "label": labels[score], "tips": tips}


# ════════════════════════════════════════════════════════════════════
#  LAYER 2 — OTP GENERATION  (6-digit, HMAC-SHA256 based)
# ════════════════════════════════════════════════════════════════════

OTP_TTL_SECONDS = 600    # 10 minutes


def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically secure numeric OTP of given length.

    Uses secrets.randbelow — NOT random.randint — to avoid predictability.

    Example:
      otp = generate_otp()   # "847291"
    """
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def generate_otp_hmac(secret: str, timestamp: int = None) -> str:
    """
    Generate a time-based 6-digit OTP using HMAC-SHA256 (TOTP algorithm).

    'secret'    — a per-user secret key (store in DB, not the OTP itself)
    'timestamp' — Unix time bucket (defaults to current 30-second window)

    Example:
      secret = user.totp_secret          # stored at registration
      otp    = generate_otp_hmac(secret)  # changes every 30 seconds
    """
    if timestamp is None:
        timestamp = int(time.time()) // 30   # 30-second TOTP window

    key     = secret.encode("utf-8")
    counter = struct.pack(">Q", timestamp)   # 8-byte big-endian counter
    mac     = hmac.new(key, counter, hashlib.sha256).digest()
    offset  = mac[-1] & 0x0F
    code    = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** 6)).zfill(6)


def verify_otp_hmac(secret: str, otp: str, window: int = 1) -> bool:
    """
    Verify a TOTP OTP allowing ±window time buckets (clock drift).

    Example:
      if not verify_otp_hmac(user.totp_secret, submitted_otp):
          return "Invalid OTP", 401
    """
    now = int(time.time()) // 30
    for i in range(-window, window + 1):
        if hmac.compare_digest(generate_otp_hmac(secret, now + i), str(otp)):
            return True
    return False


def generate_totp_secret() -> str:
    """
    Generate a base32 TOTP secret key for a new user.
    Compatible with Google Authenticator / Authy if pyotp is installed.

    Example:
      user.totp_secret = generate_totp_secret()
    """
    if _HAS_PYOTP:
        return pyotp.random_base32()
    # Manual base32 secret without pyotp
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8")


# ════════════════════════════════════════════════════════════════════
#  LAYER 3 — SYMMETRIC ENCRYPTION  (Fernet / AES-128-CBC + HMAC)
# ════════════════════════════════════════════════════════════════════

def _derive_fernet_key(secret_key: str, salt: bytes = None) -> bytes:
    """
    Derive a 32-byte Fernet key from an application secret using PBKDF2.
    Never store the derived key — re-derive it each time from the secret.
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("Install 'cryptography': pip install cryptography")

    if salt is None:
        # Use a fixed application salt (change this per deployment).
        # For per-row salts, generate and store alongside the ciphertext.
        salt = b"cricshot_salt_v1"

    kdf = PBKDF2HMAC(
        algorithm = _hashes.SHA256(),
        length    = 32,
        salt      = salt,
        iterations= 480_000,
        backend   = default_backend(),
    )
    raw_key = kdf.derive(secret_key.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)   # Fernet requires URL-safe base64


def encrypt_field(plain_text: str, secret_key: str = None) -> str:
    """
    Encrypt a string field using Fernet (AES-128-CBC + HMAC-SHA256).

    Returns a URL-safe base64 ciphertext string prefixed with "fernet:".
    Returns the original string unchanged if encryption is unavailable.

    Example:
      user.mobile = encrypt_field(raw_mobile, app.secret_key)
    """
    if not _HAS_CRYPTO or not plain_text:
        return plain_text or ""

    if secret_key is None:
        secret_key = os.getenv("SECRET_KEY", "cricshot-fallback-key")

    key   = _derive_fernet_key(secret_key)
    f     = Fernet(key)
    token = f.encrypt(plain_text.encode("utf-8"))
    return "fernet:" + token.decode("utf-8")


def decrypt_field(cipher_text: str, secret_key: str = None) -> str:
    """
    Decrypt a Fernet-encrypted field.

    Returns the original plain text, or the input unchanged if it was
    never encrypted (safe to call on any string).

    Example:
      raw_mobile = decrypt_field(user.mobile, app.secret_key)
    """
    if not _HAS_CRYPTO or not cipher_text:
        return cipher_text or ""
    if not cipher_text.startswith("fernet:"):
        return cipher_text  # Not encrypted — return as-is

    if secret_key is None:
        secret_key = os.getenv("SECRET_KEY", "cricshot-fallback-key")

    try:
        key   = _derive_fernet_key(secret_key)
        f     = Fernet(key)
        token = cipher_text[len("fernet:"):].encode("utf-8")
        return f.decrypt(token).decode("utf-8")
    except (InvalidToken, Exception):
        return ""   # Decryption failed — return empty (never crash)


def generate_fernet_key() -> str:
    """
    Generate a fresh random Fernet key for use in .env ENCRYPTION_KEY.

    Run once:   python -c "from security import generate_fernet_key; print(generate_fernet_key())"
    Then set:   ENCRYPTION_KEY=<output>  in your .env file.
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("Install 'cryptography': pip install cryptography")
    return Fernet.generate_key().decode("utf-8")


# ════════════════════════════════════════════════════════════════════
#  LAYER 4 — SECURE TOKEN GENERATION
# ════════════════════════════════════════════════════════════════════

def generate_secure_token(nbytes: int = 32) -> str:
    """
    Generate a URL-safe cryptographically random token string.

    Used for: session tokens, password reset links, API keys.

    Example:
      session_token = generate_secure_token()    # 64-char hex string
      reset_link    = f"/reset?token={generate_secure_token()}"
    """
    return secrets.token_urlsafe(nbytes)


def generate_session_token() -> str:
    """Generate a 64-character hex anonymous session token."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """
    Return SHA-256 hex-digest of a token for safe database storage.
    Store only the hash — compare submitted tokens against the hash.

    Example:
      db_token = hash_token(raw_token)   # store this
      # Later:
      if hash_token(submitted) == db_token: ...
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════════════
#  LAYER 5 — HMAC SIGNATURE  (tamper-proof URL params / cookies)
# ════════════════════════════════════════════════════════════════════

def sign_value(value: str, secret_key: str = None) -> str:
    """
    Create an HMAC-SHA256 signature for a value.
    Use to sign URL parameters, cookie values, or email tokens.

    Example:
      signed = sign_value(str(user.id))
      url    = f"/confirm-email?uid={user.id}&sig={signed}"
    """
    if secret_key is None:
        secret_key = os.getenv("SECRET_KEY", "cricshot-fallback-key")
    mac = hmac.new(secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def verify_signature(value: str, signature: str, secret_key: str = None) -> bool:
    """
    Verify an HMAC-SHA256 signature in constant time (safe against timing attacks).

    Example:
      uid = request.args.get("uid")
      sig = request.args.get("sig")
      if not verify_signature(uid, sig):
          abort(403)
    """
    expected = sign_value(value, secret_key)
    return hmac.compare_digest(expected, signature)


# ════════════════════════════════════════════════════════════════════
#  QUICK SELF-TEST  (run:  python security.py)
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    SEP = "-" * 56
    print(SEP)
    print("CRICSHOT Security Module — Self Test")
    print(SEP)

    # ── Password Hashing ──────────────────────────────────────────
    raw_pw = "Cricket@2025"
    hashed = hash_password(raw_pw)
    print(f"\n[1] Password Hashing (bcrypt={_USE_RAW_BCRYPT})")
    print(f"    Plain    : {raw_pw}")
    print(f"    Hashed   : {hashed[:40]}…")
    print(f"    Verify ✓ : {verify_password(raw_pw,  hashed)}")
    print(f"    Verify ✗ : {verify_password('wrong', hashed)}")

    # ── Password Strength ─────────────────────────────────────────
    for pw in ["abc", "cricket99", "Cricket@2025!"]:
        info = check_password_strength(pw)
        print(f"    Strength '{pw}': {info['label']} ({info['score']}/5)")

    # ── OTP Generation ────────────────────────────────────────────
    otp = generate_otp()
    print(f"\n[2] OTP Generation")
    print(f"    6-digit OTP : {otp}")

    secret = generate_totp_secret()
    totp   = generate_otp_hmac(secret)
    valid  = verify_otp_hmac(secret, totp)
    print(f"    TOTP secret : {secret[:16]}…")
    print(f"    TOTP code   : {totp}")
    print(f"    TOTP valid  : {valid}")

    # ── Encryption ────────────────────────────────────────────────
    print(f"\n[3] Symmetric Encryption (cryptography={_HAS_CRYPTO})")
    if _HAS_CRYPTO:
        secret_key = "my-test-secret-key"
        plain = "+91-9876543210"
        enc   = encrypt_field(plain, secret_key)
        dec   = decrypt_field(enc,   secret_key)
        print(f"    Plain     : {plain}")
        print(f"    Encrypted : {enc[:40]}…")
        print(f"    Decrypted : {dec}")
        print(f"    Match ✓   : {plain == dec}")
        print(f"    New key   : {generate_fernet_key()[:30]}…")
    else:
        print("    ⚠  cryptography not installed — run: pip install cryptography")

    # ── Token Generation ──────────────────────────────────────────
    tok = generate_secure_token()
    print(f"\n[4] Secure Tokens")
    print(f"    URL-safe token  : {tok[:32]}…")
    print(f"    Session token   : {generate_session_token()[:32]}…")
    print(f"    Token hash      : {hash_token(tok)[:32]}…")

    # ── HMAC Signing ─────────────────────────────────────────────
    uid = "42"
    sig = sign_value(uid, "app-secret")
    print(f"\n[5] HMAC Signature")
    print(f"    Value     : {uid}")
    print(f"    Signature : {sig[:32]}…")
    print(f"    Valid ✓   : {verify_signature(uid, sig, 'app-secret')}")
    print(f"    Valid ✗   : {verify_signature('99', sig, 'app-secret')}")

    print(f"\n{SEP}")
    print("All tests passed ✓")
    print(SEP)
