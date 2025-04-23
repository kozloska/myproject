from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from ..models import Question, Project
from ..serializers import QuestionSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return Question.objects.filter(ID_Project=project_id)
        return super().get_queryset()

    @action(detail=False, methods=['GET'])
    def by_project(self, request):
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

            # Проверяем статус проекта
        if project.Status:
            # Получаем вопросы, связанные с проектом
            questions = Question.objects.filter(ID_Project=project_id).values('ID', 'Text')
            return Response(list(questions), status=status.HTTP_200_OK)
        else:
            # Если статус проекта False, возвращаем сообщение
            return Response([{'Text': "Вопросы еще не обработаны"}], status=status.HTTP_200_OK)

    @action(detail=False, methods=['DELETE'])
    def delete(self, request):
        question_id = request.query_params.get('question_id')
        try:
            # Получаем вопрос по ID
            question = Question.objects.get(ID=question_id)

            # Удаляем вопрос
            question.delete()

            # Возвращаем сообщение об успешном удалении
            return Response({'message': 'Вопрос успешно удален'}, status=status.HTTP_200_OK)

        except Question.DoesNotExist:
            # Если вопрос не найден, возвращаем ошибку 404
            return Response({'error': 'Вопрос не найден'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            # Обрабатываем другие исключения
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['PUT'])
    def update_question(self, request):
        question_id = request.query_params.get('question_id')
        try:
            # Получаем вопрос по ID
            question = Question.objects.get(ID=question_id)

            # Получаем новый текст вопроса из тела запроса
            new_text = request.query_params.get('text')

            # Обновляем текст вопроса
            question.Text = new_text
            question.save()

            # Возвращаем обновленный вопрос
            return Response({'ID': question.ID, 'Text': question.Text}, status=status.HTTP_200_OK)

        except Question.DoesNotExist:
            # Если вопрос не найден, возвращаем ошибку 404
            return Response({'error': 'Вопрос не найден'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            # Обрабатываем другие исключения
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['POST'])
    def create_question(self, request):
        try:
            # Получаем текст нового вопроса и ID проекта из тела запроса
            text = request.data.get('text')
            project_id = request.data.get('project_id')

            # Проверяем, что текст вопроса и ID проекта существуют
            if not text:
                return Response({'error': 'Текст вопроса обязателен'}, status=status.HTTP_400_BAD_REQUEST)
            if not project_id:
                return Response({'error': 'ID проекта обязателен'}, status=status.HTTP_400_BAD_REQUEST)

            # Получаем проект по ID
            project = Project.objects.get(ID=project_id)

            # Создаем новый вопрос, связанный с проектом
            new_question = Question(Text=text, ID_Project=project)
            new_question.save()

            # Возвращаем созданный вопрос
            return Response({
                'ID': new_question.ID,
                'Text': new_question.Text,
                'Project_ID': new_question.ID_Project.ID
            }, status=status.HTTP_201_CREATED)

        except Project.DoesNotExist:
            # Если проект не найден, возвращаем ошибку 404
            return Response({'error': 'Проект не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Обрабатываем другие исключения
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)