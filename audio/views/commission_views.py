from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from ..filters import CommissionFilter
from ..models import Commission, CommissionComposition, CommissionMember
from ..serializers import CommissionSerializer, CommissionCompositionSerializer, CommissionMemberSerializer


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CommissionFilter
