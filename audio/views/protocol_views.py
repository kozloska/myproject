from django_filters.rest_framework import DjangoFilterBackend

from ..filters import ProtocolFilter
from ..models import Protocol, Student
from ..serializers import ProtocolSerializer, UpdateGradeSerializer, ProtocolArchiveLiteSerializer
from rest_framework import viewsets, status


class ProtocolViewSet(viewsets.ModelViewSet):
    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter  

    def get_queryset(self):
        queryset = Protocol.objects.select_related(
            'ID_Student',                          # Студент
            'ID_Student__ID_Group',                # Группа студента
            'ID_Student__ID_Specialization',       # Специализация студента
            'ID_Student__ID_Project',              # Проект студента
            'ID_Student__ID_Qualification',        # Квалификация студента
            'ID_DefenseSchedule',                  # Расписание защиты
            'ID_DefenseSchedule__ID_Commission',   # Комиссия
        ).all()
        return queryset.order_by('-Year', 'Number')
    
    def perform_update(self, serializer):
        # 1. Сохраняем изменения в протоколе
        protocol = serializer.save()
        
        # 2. Проверяем, что запрос касался изменения расписания
        if 'ID_DefenseSchedule' in self.request.data:
            # 3. Безопасно добираемся до проекта
            if protocol.ID_Student and protocol.ID_Student.ID_Project:
                project = protocol.ID_Student.ID_Project
                
                # 4. Обновляем статус (только это поле, чтобы не триггерить лишние сигналы)
                project.Status = "Защита не начата"
                project.save(update_fields=['Status'])

class ProtocolArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProtocolArchiveLiteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter
    
    def get_queryset(self):
        return Protocol.objects.select_related(
            'ID_Student',
            'ID_Student__ID_Group',
            'ID_Student__ID_Specialization',
            'ID_Student__ID_Project',
            'ID_DefenseSchedule',
        ).filter(Status=True).order_by('-Year', 'Number')