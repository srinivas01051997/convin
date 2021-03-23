from . import views
from django.urls import path

urlpatterns = [
	path('task', views.task),
	path('task-tracker', views.task_tracker),
]
