from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from audio.filters import SecretarySpecializationFilter
from audio.serializers import SecretarySpecialization, SecretarySpecializationSerializer

class SecretarySpecializationViewSet(viewsets.ModelViewSet):
    queryset = SecretarySpecialization.objects.all()
    serializer_class = SecretarySpecializationSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SecretarySpecializationFilter  # Используйте новый фильтр
