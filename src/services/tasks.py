from datetime import datetime, timezone

from database.crud.accounts import get_all_activation_tokens, remove_activation_token
from database.session_postgresql import get_postgresql_db
from services.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def review_activation_token() -> None:
    db = next(get_postgresql_db())
    try:
        activation_tokens = get_all_activation_tokens(db)
        for activation_token in activation_tokens:
            if (activation_token.expires_at.replace(tzinfo=timezone.utc) <
                    datetime.now(timezone.utc)):
                remove_activation_token(db=db, activation_token=activation_token.token)
    finally:
        db.close()
        logger.info("Remove expired token completed")
