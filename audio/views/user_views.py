from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from tutorial.quickstart.serializers import UserSerializer

from ..models import User, CommissionMember, SecretarySpecialization, CommissionComposition, Specialization, Commission
import logging

logger = logging.getLogger(__name__)  # Получаем логгер
"""
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()


    @action(detail=False, methods=['POST'])
    def authorize_member(self, request):
        
        surname = request.data.get('surname')
        name = request.data.get('name')
        patronymic = request.data.get('patronymic')

        try:
            member = CommissionMember.objects.get(
                Surname=surname,
                Name=name,
                Patronymic=patronymic
            )
            return Response({
                'id': member.ID,
                'full_name': f"{surname} {name} {patronymic}"
            })
        except CommissionMember.DoesNotExist:
            return Response(
                {'error': 'Член комиссии не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


    @action(detail=False, methods=['GET'])
    def specializations(self, request):
        
        secretary_id = request.query_params.get('secretary_id')
        logger.info("Метод specializations вызван")
        secretary_id = request.query_params.get('secretary_id')
        specializations = SecretarySpecialization.objects.filter(ID_Secretary_id=secretary_id).values(
            'ID_Specialization_id')
        # Получаем список ID специализаций
        specialization_ids = [spec['ID_Specialization_id'] for spec in specializations]
        # Получаем специализации по ID
        specializations_list = Specialization.objects.filter(ID__in=specialization_ids).values('ID', 'Name')
        return Response(list(specializations_list), status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def commissions(self, request):
        
        member_id = request.query_params.get('secretary_id')
        # Получаем комиссии, в которых есть указанный член комиссии
        commissions = Commission.objects.filter(
            commissioncomposition__ID_Member=member_id,
            commissioncomposition__Role='Секретарь'
        ).values('ID', 'Name')  # Извлекаем ID и Name
        if not commissions:
            return Response(
                {'message': 'Комиссии не найдены для данного члена комиссии.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(commissions, status=status.HTTP_200_OK)
"""