# audio/urls.py
from django.urls import path
from .views import upload_audio, specialization_list, commission_list, defense_schedule_list, \
    add_commission_to_schedule, project_list, students_by_project, questions_by_project

urlpatterns = [
    path('upload/', upload_audio, name='upload_audio'),
    path('specializations/', specialization_list, name='specialization_list'),
    path('commissions/', commission_list, name='commission_list'),
    path('defense_schedules/', defense_schedule_list, name='defense_schedule_list'),
    path('projects/', project_list, name='project_list'),
    path('defense_schedules/addComission/', add_commission_to_schedule, name='add_commission_to_schedule'),
    path('students_by_project/', students_by_project, name='students_by_project'),
    path('questions_by_project/', questions_by_project, name='questions_by_project'),
]
