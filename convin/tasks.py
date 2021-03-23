import json

from django.core.exceptions import ObjectDoesNotExist

from .models import Log
from .celery import app
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule


def send_email_to_celery_scheduler(email=None, tasks=None, tracker_description=None, update_type=None):
    is_interval_scheduler=False
    if update_type is None:
        return
    if update_type=="now":
        schedule = IntervalSchedule.objects.create(every=10, period=IntervalSchedule.SECONDS)
        is_interval_scheduler=True
    if update_type=="daily":
        schedule = CrontabSchedule.objects.create(minute='0', hour='17', day_of_week='*',
                                                  day_of_month='*', month_of_year='*')
    if update_type=="weekly":
        schedule = CrontabSchedule.objects.create(minute='0', hour='0', day_of_week='1',
                                                  day_of_month='*', month_of_year='*')
    if update_type=="monthly":
        schedule = CrontabSchedule.objects.create(minute='0', hour='0', day_of_week='*',
                                                  day_of_month='1', month_of_year='*')
    if is_interval_scheduler is False:
        PeriodicTask.objects.create(crontab=schedule, name=tracker_description, task='convin.tasks.email_logs', args=json.dumps([email, tasks]))
    else:
        print("\n interval about to schedule")
        PeriodicTask.objects.create(interval=schedule, name=tracker_description, task='convin.tasks.email_logs', args=json.dumps([email, tasks]))


@app.task
def email_logs(email=None, tasks=None):
    try:
        log=Log.objects.get(email=email)
        log.delete()
    except ObjectDoesNotExist:
        pass
    Log.objects.create(email=email, tasks=tasks)
    return "successfully logged"
