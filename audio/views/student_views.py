from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from audio.filters import StudentFilter
from audio.models import Student, Protocol
from audio.serializers import StudentSerializer, UpdateGradeSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().select_related(
        'ID_Group', 'ID_Specialization', 'ID_Project'
    ).prefetch_related('protocol_set')
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StudentFilter

    @action(detail=False, methods=['patch'], serializer_class=UpdateGradeSerializer)
    def update_grade(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Проверяем данные

        student_id = serializer.validated_data['ID_Student']
        new_grade = serializer.validated_data['Grade']

        try:
            protocol = Protocol.objects.get(ID_Student=student_id)
            student = Student.objects.get(ID=student_id)

            if new_grade == "Пересдача":
                # Не устанавливаем оценку, сбрасываем ID_DefenseSchedule
                protocol.ID_DefenseSchedule = None
                protocol.save()

                # Обновляем статус проекта
                if student.ID_Project:
                    student.ID_Project.Status = "Защита не начата"
                    student.ID_Project.save()

                return Response({"status": "Установлен статус пересдачи, защита сброшена"})
            else:
                # Обычная логика обновления оценки
                protocol.Grade = new_grade
                protocol.save()
                return Response({"status": "Оценка обновлена!"})

        except Protocol.DoesNotExist:
            return Response(
                {"error": "Протокол для этого студента не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Student.DoesNotExist:
            return Response(
                {"error": "Студент не найден"},
                status=status.HTTP_404_NOT_FOUND
            )