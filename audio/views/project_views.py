from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Project, Student, Protocol
from ..serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=False, methods=['GET'])
    def by_defense_schedule(self, request):
        defense_schedule_id = request.query_params.get('defense_schedule_id')
        projects = Project.objects.filter(
            ID__in=Protocol.objects.filter(
                ID_DefenseSchedule=defense_schedule_id
            ).values('ID_Student__ID_Project')
        ).values('ID', 'Title', 'Supervisor')

        project_list = list(projects)
        return Response(project_list, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def students(self, request):
        try:
            # Получаем project_id из параметров запроса
            project_id = request.query_params.get('project_id')

            if project_id is None:
                return Response({'error': 'project_id не предоставлен'}, status=status.HTTP_400_BAD_REQUEST)

            # Преобразуем project_id в целое число
            project_id = int(project_id)

            # Получаем проект по ID
            project = Project.objects.get(ID=project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Проект не найден'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Неверный формат project_id'}, status=status.HTTP_400_BAD_REQUEST)

            # Получаем студентов, связанных с проектом
        students = Student.objects.filter(ID_Project=project_id).values('ID', 'Surname', 'Name', 'Patronymic')
        return Response(list(students), status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def grade(self, request):
        try:
            # Получаем данные из тела запроса
            student_id = request.data.get('student_id')
            grade = request.data.get('grade')

            # Получаем студента по ID
            student = Student.objects.get(ID=student_id)

            protocol = Protocol.objects.get(ID_Student=student.ID)

            if protocol:
                # Обновляем оценку в протоколе
                protocol.Grade = grade
                protocol.save()

                # Возвращаем информацию об обновленной оценке
                return Response({
                    'student_id': student_id,
                    'grade': grade
                }, status=status.HTTP_200_OK)
            else:
                # Если протокол не найден, возвращаем ошибку 404
                return Response({'error': 'Протокол не найден'}, status=status.HTTP_404_NOT_FOUND)

        except Student.DoesNotExist:
            # Если студент не найден, возвращаем ошибку 404
            return Response({'error': 'Студент не найден'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            # Обрабатываем другие исключения
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)