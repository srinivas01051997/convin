import json

from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from rest_framework.parsers import JSONParser
from django.shortcuts import render
from convin.models import Task, TaskTracker, Log
from django.views.decorators.csrf import csrf_exempt
from ratelimit.decorators import ratelimit
from convin.serializers import TaskSerializer, TaskTrackerSerializer
from convin.celery import app
from convin.tasks import send_email_to_celery_scheduler
from datetime import datetime, timedelta


# Create your views here.


def get_task(task_id=None):
    try:
        task = Task.objects.get(id=task_id)
    except ObjectDoesNotExist:
        task = None
    return task


def serialized_data_to_dict(data=None):
    """
    objective: this is a support function to convert the serialized data into native python datatype
    :param data: this is an ORM serialized object
    :return: json object
    """
    json_dumped_data = json.dumps(data, cls=DjangoJSONEncoder)
    json_data = json.loads(json_dumped_data)
    return json_data


@ratelimit(key='ip', rate='10/m', block=True, method=ratelimit.ALL)
@csrf_exempt
def task(request=None):
    if request.method == "POST":
        """ to create a new task """
        try:
            try:
                # parse the data
                data = JSONParser().parse(request)
            except:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # read data
            task_type = data.get('task_type')
            task_desc = data.get("task_desc")
            # check whether all mandatory parameters are received or not
            if task_type is None or task_desc is None or task_type == "":
                return JsonResponse({"error": "Missing mandatory fields"}, status=422)
            else:
                task_desc=task_desc.strip()
                if task_desc is None or task_desc=="":
                    return JsonResponse({"error": "Missing mandatory fields"}, status=422)
            # check type of parameters
            if isinstance(task_type, int) is False or isinstance(task_desc, str) is False:
                return JsonResponse({"error": "Invalid Payload"}, status=422)
            # check whether garbage is sent in 'task_type' parameter
            if task_type not in [1, 2, 3, 4]:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # create task
            task = Task.objects.create(task_type=task_type, task_desc=task_desc)
            task = TaskSerializer(task).data
            return JsonResponse({"data": task}, status=200)
        except Exception:
            return JsonResponse({"error": "Something went wrong"}, status=400)
    elif request.method == "PUT":
        """ to update a task """
        try:
            try:
                # parse the data
                data = JSONParser().parse(request)
            except:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # read data
            task_id = data.get('task_id')
            task_type = data.get('task_type')
            task_desc = data.get("task_desc")
            # check whether all mandatory parameters are received or not
            if task_id is None or (task_type is None and task_desc is None and task_type == ""):
                return JsonResponse({"error": "Missing mandatory fields"}, status=422)
            # check type of parameters
            if task_type and isinstance(task_type, int) is False:
                return JsonResponse({"error": "Invalid Payload"}, status=422)
            if task_desc and isinstance(task_desc, str) is False:
                return JsonResponse({"error": "Invalid Payload"}, status=422)
            # check whether garbage is sent in 'task_type' parameter
            if task_type and task_type not in [1, 2, 3, 4]:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # get task
            task = get_task(task_id=task_id)
            if task is None:
                return JsonResponse({"error": "No such task exists"}, status=404)
            if task_type:
                task.task_type=task_type
            if task_desc:
                task_desc=task_desc.strip()
                if task_desc is None or task_desc=='':
                    return JsonResponse({"error": "Invalid payload"}, status=422)
                task.task_desc = task_desc
            task.save()
            task = get_task(task_id=task_id)
            if task is None:
                return JsonResponse({"error": "No such task exists"}, status=404)
            task = TaskSerializer(task).data
            return JsonResponse({"datae": task}, status=200)
        except Exception:
            return JsonResponse({"error": "Something went wrong"}, status=400)
    else:
        return JsonResponse({"error": "Internal Server Error"}, status=500)


@ratelimit(key='ip', rate='10/m', block=True, method=ratelimit.ALL)
@csrf_exempt
def task_tracker(request=None):
    if request.method == "POST":
        """ to create a new task tracker """
        try:
            tracker=None
            try:
                # parse the data
                data = JSONParser().parse(request)
            except:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # read data
            task_id = data.get("task_id")
            update_type = data.get("update_type")
            email = data.get("email")
            tracker_description = data.get("tracker_description")
            # check whether all mandatory parameters are received or not
            if tracker_description is None or task_id is None or update_type is None or email is None or email=='':
                return JsonResponse({"error": "Missing mandatory fields"}, status=422)
            else:
                update_type=update_type.strip().lower()
                if update_type is None or update_type=="":
                    return JsonResponse({"error": "Missing mandatory fields"}, status=422)
            # check type of parameters
            if isinstance(task_id, str) is False or isinstance(update_type, str) is False:
                return JsonResponse({"error": "Invalid Payload"}, status=422)
            if update_type not in ["weekly", "daily", "monthly", "now"]:
                return JsonResponse({"error": "Invalid payload"}, status=422)
            # get task
            task = get_task(task_id=task_id)
            if task is None:
                return JsonResponse({"error": "No such task exists"}, status=404)
            # create task
            tracker = TaskTracker.objects.create(task=task, email=email)
            # update the update also
            task.update_type=update_type
            task.save()
            # get the tasks data that has to be scheduled
            tasks = get_task_reports(email=email, task=task, update_type=update_type)
            # schedule the job
            send_email_to_celery_scheduler(email=email, tasks=tasks, tracker_description=tracker_description,
                                           update_type=update_type)
            return JsonResponse(tasks, status=200)
        except Exception as e:
            print("\n Exception = ", e)
            if tracker:
                tracker.delete()
            return JsonResponse({"error": "Something went wrong"}, status=400)
    else:
        return JsonResponse({"error": "Internal Server Error"}, status=500)


def get_task_reports(email=None, task=None, update_type=None):
    current_datetime = datetime.now()
    if update_type in ["daily", "now"]:
        earlier_datetime=current_datetime - timedelta(hours=24)
    if update_type=="weekly":
        earlier_datetime = current_datetime - timedelta(days=7)
    if update_type=="monthly":
        earlier_datetime = datetime.now() - timedelta(weeks=4)
    tasks=TaskTracker.objects.filter(email=email, task=task, created_on__range=(earlier_datetime, current_datetime))
    tasks=TaskTrackerSerializer(tasks, many=True).data
    tasks=serialized_data_to_dict(data=tasks)
    return {"data": tasks}
