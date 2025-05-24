from django_filters.rest_framework import DjangoFilterBackend

from ..filters import ProtocolFilter
from ..models import Protocol, Student
from ..serializers import ProtocolSerializer, UpdateGradeSerializer
from rest_framework import viewsets, status


class ProtocolViewSet(viewsets.ModelViewSet):
    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter  # Используем наш кастомный фильтр