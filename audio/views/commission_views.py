from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Commission, CommissionComposition, CommissionMember
from ..serializers import CommissionSerializer, CommissionCompositionSerializer, CommissionMemberSerializer

class CommissionViewSet(viewsets.ModelViewSet):
    queryset = CommissionComposition.objects.all()
    serializer_class = CommissionCompositionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ID_Member', 'Role']
