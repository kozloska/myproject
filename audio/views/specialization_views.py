from django_filters.rest_framework import DjangoFilterBackend
from ..models import Question, Project, Specialization
from ..serializers import QuestionSerializer, SpecializationSerializer
from rest_framework import viewsets


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer