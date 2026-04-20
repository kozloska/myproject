from django_filters.rest_framework import DjangoFilterBackend
from audio.services.parse_excel_file import get_next_protocol_number
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
        serializer.is_valid(raise_exception=True)

        student = serializer.validated_data['ID_Student']
        new_grade = serializer.validated_data['Grade']

        try:
            protocol = Protocol.objects.get(ID_Student=student)

            if new_grade == "Пересдача":
                # Не устанавливаем оценку, сбрасываем защиту
                protocol.ID_DefenseSchedule = None
                protocol.DefenseStartTime = None
                protocol.DefenseEndTime = None
                protocol.save()

               # if student.ID_Project:
                #    student.ID_Project.Status = "Защита не начата"
                #    student.ID_Project.save()

                return Response({"status": "Установлен статус пересдачи"})

            else:
                # Обычная оценка + присвоение номера (только если ещё нет)
                protocol.Grade = new_grade

                if not protocol.Number or protocol.Number.strip() == '':
                    spec = student.ID_Specialization
                    year = protocol.Year
                    next_seq = get_next_protocol_number(spec, year)
                    protocol.Number = f"{next_seq}-{spec.Number}-{year}"

                protocol.save()
                return Response({"status": "Оценка обновлена!"})

        except Protocol.DoesNotExist:
            return Response({"error": "Протокол для этого студента не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:  # на случай других ошибок
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
