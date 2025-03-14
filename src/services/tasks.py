from datetime import datetime, timezone
from asgiref.sync import async_to_sync
from src.database.crud.accounts import (
    get_all_activation_tokens,
    remove_activation_token
)
from src.database.session_postgresql import get_postgresql_db
from src.services.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def remove_expired_activation_tokens() -> None:
    async def async_task():
        async for db in get_postgresql_db():
            try:
                activation_tokens = await get_all_activation_tokens(db)
                now = datetime.now(timezone.utc)

                for activation_token in activation_tokens:
                    if activation_token.expires_at.replace(
                            tzinfo=timezone.utc
                    ) < now:
                        await remove_activation_token(
                            db=db,
                            token=activation_token
                        )

                logger.info("Expired activation tokens removed successfully.")
            finally:
                await db.close()

    async_to_sync(async_task)()
