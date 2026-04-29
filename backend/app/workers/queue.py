"""RQ queue dependency. Tests override this to use a fake queue."""

from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import settings


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    return Queue("audits", connection=Redis.from_url(settings.redis_url))
