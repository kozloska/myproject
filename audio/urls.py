from django.urls import path, include
from rest_framework.routers import DefaultRouter

from audio.views.audio_views import upload_audio
from audio.views.project_views import ProjectViewSet
from audio.views.question_views import QuestionViewSet
from audio.views.secretarySpecialization_views import SecretarySpecializationViewSet
from audio.views.secretary_views import SecretaryViewSet

"""from audio.views.commission_views import CommissionViewSet
from audio.views.defense_views import DefenseViewSet
from audio.views.project_views import ProjectViewSet
from audio.views.project_views import ProjetNewiewSet
from audio.views.question_views import QuestionViewSet
from audio.views.user_views import UserViewSet
"""

router = DefaultRouter()
"""
router.register(r'users', UserViewSet, basename='user')
router.register(r'proj', ProjetNewiewSet, basename='proj')
router.register(r'projects', ProjectViewSet, basename='project')"""
router.register(r'secretary', SecretaryViewSet, basename='secretary')
router.register(r'secretary_specialization', SecretarySpecializationViewSet, basename='secretary_specialization')
router.register(r'questions', QuestionViewSet, basename='question')
"""
router.register(r'commissions', CommissionViewSet, basename='commission')
router.register(r'defenses', DefenseViewSet, basename='defense')"""

urlpatterns = [
    path('', include(router.urls)),
    path('upload-audio/', upload_audio, name='upload-audio')
]


