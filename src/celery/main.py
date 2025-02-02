# from celery import Celery
#
#
# redis_url = "redis://localhost:6379/0"
#
# celery_app = Celery("celery_worker", broker=redis_url, backend=redis_url)
#
# @celery_app.task
# def add(x, y):
#     print("Celery task executed")
#
# celery_app.conf.beat_schedule = {
#     'add-task': {
#         'task': 'src.celery.main.add',  # Вказуємо повний шлях до задачі
#         'schedule': 10.0,  # Інтервал виконання (кожні 10 секунд)
#         'args': (10, 20),  # Аргументи, які передаються задачі
#     },
# }