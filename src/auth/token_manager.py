from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Redis connection for storing refresh tokens
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Secret keys from environment variables
REFRESH_SECRET_KEY = os.getenv("REFRESH_TOKEN_SECRET_KEY", "your-default-refresh-secret-key-change-this-in-production")
ALGORITHM = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

def store_refresh_token(user_id: int, token: str, expires_at: datetime):
    """
    Store refresh token in Redis with expiration
    """
    key = f"refresh_token:{user_id}:{token}"
    ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
    redis_client.setex(key, ttl_seconds, "valid")

def invalidate_refresh_token(user_id: int, token: str):
    """
    Invalidate a refresh token in Redis
    """
    key = f"refresh_token:{user_id}:{token}"
    redis_client.delete(key)

def is_refresh_token_valid(user_id: int, token: str) -> bool:
    """
    Check if refresh token is valid in Redis
    """
    key = f"refresh_token:{user_id}:{token}"
    return redis_client.exists(key) == 1

def revoke_all_refresh_tokens(user_id: int):
    """
    Revoke all refresh tokens for a user
    """
    pattern = f"refresh_token:{user_id}:*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        jti: str = payload.get("jti")  # JWT ID for tracking

        if user_id is None or jti is None:
            return None

        # Check if the refresh token is still valid in Redis
        if not is_refresh_token_valid(user_id, jti):
            return None

        return {"user_id": user_id, "jti": jti}
    except JWTError:
        return None