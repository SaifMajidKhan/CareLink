import hashlib, hmac, secrets, time
from collections import defaultdict, deque
from fastapi import HTTPException

def password_hash(value):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(value.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()

def verify_password(value, stored):
    salt, expected = stored.split(':')
    actual = hashlib.scrypt(value.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

class RateLimit:
    def __init__(self): self.calls = defaultdict(deque)
    def check(self, key, limit=20):
        now = time.monotonic()
        bucket = self.calls[key]
        while bucket and bucket[0] < now - 300: bucket.popleft()
        if len(bucket) >= limit: raise HTTPException(429, 'Too many requests. Try again in five minutes.')
        bucket.append(now)
