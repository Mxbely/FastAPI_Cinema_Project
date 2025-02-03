from routes.accounts import remove_all_expired_activation_tokens
from services.celery_app import celery_app


@celery_app.task
def review_activation_token():
    remove_all_expired_activation_tokens()
    print("Celery task completed")
