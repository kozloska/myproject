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
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            project_id = serializer.validated_data['ID_Project']
            defense_time = serializer.validated_data.get('DefenseStartTime')
            updated = Protocol.objects.filter(
                ID_Student__in=Student.objects.filter(ID_Project=project_id).values('ID')
            ).update(DefenseStartTime=defense_time)

            project = Project.objects.get(ID=project_id)
            if defense_time is None:
                project.Status = "Защита не начата"
            else:
                project.Status = "Защита начата"
            project.save()
            return Response({"message": "Протоколы успешно обновлены"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'], serializer_class=UpdateDefenseTimeEndByProjectSerializer)
    def project_time_end(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            project_id = serializer.validated_data['ID_Project']
            defense_time = serializer.validated_data.get('DefenseEndTime')
            updated = Protocol.objects.filter(
                ID_Student__in=Student.objects.filter(ID_Project=project_id).values('ID')
            ).update(DefenseEndTime=defense_time)

            return Response({"message": "Протоколы успешно обновлены"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

