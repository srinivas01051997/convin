import json
import uuid
from django.core.exceptions import ObjectDoesNotExist

from .models import Log
from .celery import app
from django_celery_beat.models import PeriodicTask, CrontabSchedule


def send_email_to_celery_scheduler(email=None, tasks=None, update_type=None):
    if update_type=="daily":
        schedule = CrontabSchedule.objects.create(minute='0', hour='17', day_of_week='*',
                                                  day_of_month='*', month_of_year='*')
    if update_type=="weekly":
        schedule = CrontabSchedule.objects.create(minute='0', hour='0', day_of_week='1',
                                                  day_of_month='*', month_of_year='*')
    if update_type=="monthly":
        schedule = CrontabSchedule.objects.create(minute='0', hour='0', day_of_week='*',
                                                  day_of_month='1', month_of_year='*')
    PeriodicTask.objects.create(crontab=schedule, name=str(uuid.uuid4()), task='convin.tasks.email_logs',
                                args=json.dumps([email, tasks]))


@app.task
def email_logs(email=None, tasks=None):
    try:
        log=Log.objects.get(email=email)
        log.delete()
    except ObjectDoesNotExist:
        pass
    Log.objects.create(email=email, tasks=tasks)
    return "successfully logged"
