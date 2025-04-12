from django.urls import path, include
from rest_framework.routers import DefaultRouter

from audio.views.audio_views import upload_audio
from audio.views.commission_views import CommissionViewSet
from audio.views.defense_views import DefenseViewSet
from audio.views.project_views import ProjectViewSet
from audio.views.question_views import QuestionViewSet
from audio.views.user_views import UserViewSet


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'commissions', CommissionViewSet, basename='commission')
router.register(r'defenses', DefenseViewSet, basename='defense')

urlpatterns = [
    path('', include(router.urls)),
    path('upload-audio/', upload_audio, name='upload-audio')
]


