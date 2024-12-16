# audio/urls.py
from django.urls import path
from .views import upload_audio, specialization_list

urlpatterns = [
    path('upload/', upload_audio, name='upload_audio'),
    path('specializations/', specialization_list, name='specialization-list'),
]
