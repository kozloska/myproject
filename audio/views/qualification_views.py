from django_filters.rest_framework import DjangoFilterBackend
from ..models import Qualification, Project, Specialization
from ..serializers import QuestionSerializer, QualificationSerializer
from rest_framework import viewsets


class QualificationViewSet(viewsets.ModelViewSet):
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ID_Specialization']