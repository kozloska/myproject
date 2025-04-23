from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from datetime import datetime
from ..models import (
    DefenseSchedule,
    Project,
    Specialization,
    Protocol,
    Student
)


class DefenseViewSet(viewsets.ModelViewSet):
    queryset = DefenseSchedule.objects.all()


    @action(detail=False, methods=['GET'])
    def today(self, request):
        """Получить сегодняшние защиты по специализации"""
        specialization_id = request.query_params.get('specialization_id')
        date_str = request.query_params.get('date')
        try:
            # Получаем направление по ID
            specialization = Specialization.objects.get(ID=specialization_id)

            # Преобразуем строку даты в объект datetime
            defense_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Получаем расписания защит через протокол
            defenses = DefenseSchedule.objects.filter(
                protocol__ID_Student__ID_Specialization=specialization,
                DateTime__date=defense_date
            ).distinct()

            # Формируем ответ
            response_data = [
                {'ID': defense.ID, 'DateTime': defense.DateTime}
                for defense in defenses
            ]

            return Response(response_data, status=status.HTTP_200_OK)

        except Specialization.DoesNotExist:
            return Response({'error': 'Specialization not found'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['POST'])
    def add_commission(self, request):
        """Добавить комиссию к расписанию защиты"""

        try:
            commission_id = request.data.get('commissionId')
            schedule_id = request.data.get('scheduleId')

            # Найти запись в таблице DefenseSchedule по schedule_id
            defense_schedule = DefenseSchedule.objects.filter(ID=schedule_id).first()

            if not defense_schedule:
                return Response({"error": "Расписание не найдено."}, status=status.HTTP_404_NOT_FOUND)

            # Обновляем ID комиссии
            defense_schedule.ID_Commission_id = commission_id

            defense_schedule.save()  # Сохраняем изменения в базе данных

            return Response({"message": "Комиссия успешно добавлена в расписание."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['GET'])
    def projects(self, request, pk=None):
        """Получить проекты для конкретной защиты"""
        defense = self.get_object()

        projects = Project.objects.filter(
            ID__in=Protocol.objects.filter(
                ID_DefenseSchedule=defense.ID
            ).values('ID_Student__ID_Project')
        )

        return Response([{
            'ID': p.ID,
            'Title': p.Title,
            'Supervisor': p.Supervisor,
            'Status': p.Status
        } for p in projects])

    @action(detail=False, methods=['GET'])
    def by_specialization(self, request):
        """Получить защиты по специализации и дате"""
        try:
            specialization_id = request.query_params.get('specialization_id')
            date_str = request.query_params.get('date')

            if not specialization_id:
                return Response(
                    {'error': 'specialization_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = DefenseSchedule.objects.all()

            if date_str:
                defense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(DateTime__date=defense_date)

            queryset = queryset.filter(
                protocol__ID_Student__ID_Specialization=specialization_id
            ).distinct()

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

