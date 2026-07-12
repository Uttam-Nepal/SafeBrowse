"""
auth.py — password hashing + JWT token creation/verification.

JWT (JSON Web Token) is how the frontend proves "this request is from
a logged-in user" on every subsequent request, without re-sending the
password each time: after login, the backend hands back a signed token;
the frontend stores it and attaches it to future requests; the backend
verifies the signature to trust who's asking.
"""

import os
from datetime import datetime, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext

# In production, set this via an environment variable — never commit a
# real secret key to Git. For local dev, this default is fine.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-secret-change-this-before-deploying")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None