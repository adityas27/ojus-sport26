import os
from django.conf import settings
from django.db import DatabaseError
from .models import Bookings

TOTAL_CAPACITY = 1200


def _get_redis_client():
    url = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('REDIS_URL')
    if not url:
        return None
    try:
        import redis
        # redis.from_url supports rediss:// as well
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def set_remaining_cache(remaining, ttl=5):
    client = _get_redis_client()
    if not client:
        return False
    try:
        client.set('remaining_seats', str(remaining), ex=ttl)
        return True
    except Exception:
        return False


def get_remaining_seats():
    """Return remaining seats. Prefer Redis cache, but fallback to DB if Redis unavailable.

    Always compute from DB when Redis is not available. If Redis is available,
    try to read cached value; if missing, compute from DB and set cache.
    """
    client = _get_redis_client()
    if client:
        try:
            val = client.get('remaining_seats')
            if val is not None:
                return int(val)
        except Exception:
            client = None

    # Fallback to DB
    try:
        booked = Bookings.objects.count()
    except Exception as e:
        raise DatabaseError("Unable to read bookings from DB") from e

    remaining = TOTAL_CAPACITY - booked

    # Update Redis cache if possible
    if client:
        try:
            # short TTL to keep it fresh under burst
            client.set('remaining_seats', str(remaining), ex=5)
        except Exception:
            pass

    return remaining
