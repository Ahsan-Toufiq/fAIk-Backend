import random
from datetime import datetime, timedelta

def generate_otp(length: int = 6) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def get_otp_expiration(minutes: int = 15) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)