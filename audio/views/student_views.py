from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from audio.models import Student, Protocol
from audio.serializers import StudentSerializer, UpdateGradeSerializer
from rest_framework.decorators import action
from rest_framework.response import Response


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ID_Project']

    @action(detail=False, methods=['patch'], serializer_class=UpdateGradeSerializer)
    def update_grade(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Проверяем данные

        student_id = serializer.validated_data['ID_Student']
        new_grade = serializer.validated_data['Grade']

        try:
            protocol = Protocol.objects.get(ID_Student=student_id)
            protocol.Grade = new_grade
            protocol.save()
            return Response({"status": "Оценка обновлена!"})

        except Protocol.DoesNotExist:
            return Response(
                {"error": "Протокол для этого студента не найден"},
                status=status.HTTP_404_NOT_FOUND
            )