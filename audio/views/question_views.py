from django_filters.rest_framework import DjangoFilterBackend

from ..models import Question, Project
from ..serializers import QuestionSerializer
from rest_framework import viewsets


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ID_Project']

