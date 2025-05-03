from requests import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
"""
from ..models import Commission, CommissionComposition


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all()

    @action(detail=True, methods=['GET'])
    def members(self, request, pk=None):
        members = CommissionComposition.objects.filter(ID_Commission=pk)
        return Response([{
            'ID': m.ID_Member.ID,
            'Name': m.ID_Member.Name,
            'Role': m.Role
        } for m in members])


"""