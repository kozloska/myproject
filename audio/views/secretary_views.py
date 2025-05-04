from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from ..models import CommissionMember
from ..serializers import CommissionMemberSerializer
from ..filters import SecretaryFilter

class SecretaryViewSet(viewsets.ModelViewSet):
    queryset = CommissionMember.objects.all()
    serializer_class = CommissionMemberSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SecretaryFilter
