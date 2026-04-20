from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..filters import ProjectFilter
from ..models import Project, Student, Protocol
from ..serializers import ProjectSerializer, UpdateDefenseTimeByProjectSerializer, \
    UpdateDefenseTimeEndByProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter

    @action(detail=False, methods=['patch'], serializer_class=UpdateDefenseTimeByProjectSerializer)
    def project_time_start(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        project_id = serializer.validated_data['ID_Project']
        defense_time = serializer.validated_data.get('DefenseStartTime')
        defense_schedule_id = request.data.get('ID_DefenseSchedule')
        
        # Обновляем только протоколы со статусом False и нужным расписанием
        updated = Protocol.objects.filter(
            ID_Student__in=Student.objects.filter(ID_Project=project_id).values('ID'),
            Status=False,
            ID_DefenseSchedule=defense_schedule_id
        ).update(DefenseStartTime=defense_time)

        # Обновляем статус проекта
        project = Project.objects.get(ID=project_id)
        project.Status = "Защита не начата" if defense_time is None else "Защита начата"
        project.save()
        
        return Response({
            "message": f"Протоколы успешно обновлены ({updated} записей)",
            "updated_count": updated
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], serializer_class=UpdateDefenseTimeEndByProjectSerializer)
    def project_time_end(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        project_id = serializer.validated_data['ID_Project']
        defense_time = serializer.validated_data.get('DefenseEndTime')
        defense_schedule_id = request.data.get('ID_DefenseSchedule')
        
        # Обновляем только протоколы со статусом False и нужным расписанием
        updated = Protocol.objects.filter(
            ID_Student__in=Student.objects.filter(ID_Project=project_id).values('ID'),
            Status=False,
            ID_DefenseSchedule=defense_schedule_id
        ).update(DefenseEndTime=defense_time)

        return Response({
            "message": f"Протоколы успешно обновлены ({updated} записей)",
            "updated_count": updated
        }, status=status.HTTP_200_OK)