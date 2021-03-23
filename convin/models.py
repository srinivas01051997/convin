import uuid
from django.db import models


# Create your models here.


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.IntegerField(unique=True)
    task_desc = models.CharField(max_length=100, unique=True)
    REMAINDER_FREQUENCY = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]
    update_type = models.CharField(max_length=30, choices=REMAINDER_FREQUENCY, default="daily")
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)


class TaskTracker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    email = models.EmailField(max_length=60, null=False)
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)


class Log(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=60, unique=True, null=False)
    tasks = models.JSONField(default=list)
    created_on = models.DateTimeField(auto_now_add=True)
