from celery import Celery


celery_app = Celery(
    "celery_app",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["services.tasks"],
)

celery_app.conf.beat_schedule = {
    'review_activation_token-every-day': {
        'task': 'services.tasks.review_activation_token',
        'schedule': 30.0,
    },
}
