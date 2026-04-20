from django_filters.rest_framework import DjangoFilterBackend

from ..filters import ProtocolFilter
from ..models import Protocol, Student
from ..serializers import ProtocolSerializer, UpdateGradeSerializer
from rest_framework import viewsets, status


class ProtocolViewSet(viewsets.ModelViewSet):
    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter  

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