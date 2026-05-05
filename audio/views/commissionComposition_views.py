from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from ..filters import CommissionCompositionFilter, CommissionFilter
from ..models import Commission, CommissionComposition, CommissionMember
from ..serializers import CommissionSerializer, CommissionCompositionSerializer, CommissionMemberSerializer, \
    Commission_CompositionSerializer

class CommissionCompositionViewSet(viewsets.ModelViewSet):
    queryset = CommissionComposition.objects.all()
    serializer_class = CommissionCompositionSerializer
    
    # Подключаем фильтры
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CommissionCompositionFilter
    