from django_filters.rest_framework import DjangoFilterBackend
from ..models import Question, Project
from ..serializers import QuestionSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated] 
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ID_Project', 'Status']

