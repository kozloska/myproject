from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from audio.filters import DefenseScheduleFilter
from audio.models import DefenseSchedule
from audio.serializers import DefenseScheduleSerializer, TodayDefenseQuerySerializer


class DefenseViewSet(viewsets.ModelViewSet):
    queryset = DefenseSchedule.objects.all()
    serializer_class = DefenseScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DefenseScheduleFilter  # Используем наш кастомный фильтр
