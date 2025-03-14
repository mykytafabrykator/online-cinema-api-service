from celery import Celery

from src.config import get_settings

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.services.tasks"],
)

celery_app.conf.beat_schedule = {
    "remove_expired_activation_tokens_every_hour": {
        "task": "src.services.tasks.accounts.remove_expired_activation_tokens",
        "schedule": 3600.0,  # Every hour
    },
}
