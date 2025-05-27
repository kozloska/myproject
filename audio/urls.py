from django.urls import path, include
from rest_framework.routers import DefaultRouter

from audio.services.audio_views import upload_audio
from audio.views.BitrixAuthView import BitrixAuthView
from audio.views.UploadExcelView import UploadExcelView, UploadDefenseScheduleView
from audio.views.commissionComposition_views import CommissionCompositionViewSet
from audio.views.commission_views import CommissionViewSet, CommissionMemberViewSet
from audio.views.defense_views import DefenseViewSet
from audio.views.fio_to_dative import  FIOToDativeView
from audio.views.project_views import ProjectViewSet
from audio.views.protocol_views import ProtocolViewSet
from audio.views.question_views import QuestionViewSet
from audio.views.secretarySpecialization_views import SecretarySpecializationViewSet
from audio.views.secretary_views import SecretaryViewSet
from audio.views.specialization_views import SpecializationViewSet
from audio.views.student_views import StudentViewSet


router = DefaultRouter()

router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'secretary', SecretaryViewSet, basename='secretary')
router.register(r'secretary_specialization', SecretarySpecializationViewSet, basename='secretary_specialization')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'protocols', ProtocolViewSet, basename='protocol')
router.register(r'commissions', CommissionViewSet, basename='commission')
router.register(r'commission_members', CommissionMemberViewSet, basename='commission_member')
router.register(r'commission_compositions', CommissionCompositionViewSet, basename='commission_composition')
router.register(r'defenses', DefenseViewSet, basename='defense')
router.register(r'specializations', SpecializationViewSet, basename='specialization')

urlpatterns = [
    path('', include(router.urls)),
    path('upload-audio/', upload_audio, name='upload-audio'),
    path('api/accounts/bitrix-auth/', BitrixAuthView.as_view(), name='bitrix-auth'),
    path('upload-excel/', UploadExcelView.as_view(), name='upload_excel'),
    path('upload-defense-schedule/', UploadDefenseScheduleView.as_view(), name='upload_defense_schedule'),
    path('api/fio_to_dative/', FIOToDativeView.as_view(), name='fio_to_dative'),
]


