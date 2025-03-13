# audio/urls.py
from django.urls import path
from .views import upload_audio, specialization_list, commission_list, defense_schedule_list, \
    add_commission_to_schedule, project_list, students_by_project, questions_by_project, \
    specialization_list_by_secretary, commission_list_by_member, authorize_user, \
    get_projects_by_defense_schedule_and_specialization, update_question, delete_question, update_grade, \
    create_question, get_today_defenses_by_specialization

urlpatterns = [
    path('upload/', upload_audio, name='upload_audio'),
    path('specializations/', specialization_list, name='specialization_list'),
    path('commissions/', commission_list, name='commission_list'),
    path('defense_schedules/', defense_schedule_list, name='defense_schedule_list'),
    path('projects/', project_list, name='project_list'),
    path('defense_schedules/addComission/', add_commission_to_schedule, name='add_commission_to_schedule'),
    path('students_by_project/', students_by_project, name='students_by_project'),
    path('questions_by_project/', questions_by_project, name='questions_by_project'),
    path('specializations_by_secretary/', specialization_list_by_secretary, name='specialization_list_by_secretary'),
    path('commission_list_by_member/', commission_list_by_member, name='commission_list_by_member'),
    path('authorize/', authorize_user, name='authorize-user'),
    path('update_question/', update_question, name='update_question'),
    path('delete_question/', delete_question, name='delete_question'),
    path('update_grade/', update_grade, name='update_grade'),
    path('create_question/', create_question, name='create_question'),
    path('get_today_defenses_by_specialization/', get_today_defenses_by_specialization, name='get_today_defenses_by_specialization'),
    path('get_projects_by_defense_schedule_and_specialization/', get_projects_by_defense_schedule_and_specialization, name='get_projects_by_defense_schedule_and_specialization-user'),
]

