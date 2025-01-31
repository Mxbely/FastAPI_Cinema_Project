from celery import Celery
from app.database import SessionLocal
from app.models import ActivationToken, PasswordResetToken
from datetime import datetime


celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery_app.task
def remove_expired_tokens():
    db = SessionLocal()
    db.query(ActivationToken).filter(ActivationToken.expires_at < datetime.utcnow()).delete()
    db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < datetime.utcnow()).delete()
    db.commit()
    db.close()
