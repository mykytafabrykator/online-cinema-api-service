from celery import Celery

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["services.tasks"],
)

celery_app.conf.beat_schedule = {
    "remove_expired_activation_tokens-every-hour": {
        "task": "services.tasks.remove_expired_activation_tokens",
        "schedule": 3600.0,  # Every hour
    },
}
