# audio/views.py
import os
import logging
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Specialization, Commission, DefenseSchedule, Project, Student, Question
from .serializers import AudioFileSerializer
import whisper
from pydub import AudioSegment
import spacy

# Настройка логгера
logger = logging.getLogger(__name__)

def extract_questions(text):
    nlp = spacy.load("ru_core_news_sm")
    doc = nlp(text)
    questions = []

    for sent in doc.sents:
        if sent.text.endswith('?'):
            questions.append(sent.text)

    return questions
@api_view(['POST'])
def upload_audio(request):
    logger.info("Запрос на загрузку аудио получен.")
    logger.info(f"Полученные данные: {request.data}")

    if request.method == 'POST':
        logger.debug(f"Переданные данные для сериализации: {request.data}")

        serializer = AudioFileSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.save()
            audio_file_path = default_storage.path(audio_file.audio.name)

            logger.info(f"Путь к аудиофайлу: {audio_file_path}")

            # Извлечение ID проекта
            project_id_str = request.data.get('project_id')
            if not project_id_str:
                logger.error("ID проекта не передан")
                return Response({"error": "ID проекта не передан"}, status=status.HTTP_400_BAD_REQUEST)

            # Преобразование project_id в целое число
            try:
                project_id = int(project_id_str)
            except ValueError:
                logger.error("ID проекта должен быть целым числом")
                return Response({"error": "ID проекта должен быть целым числом"}, status=status.HTTP_400_BAD_REQUEST)

            # Проверка формата файла
            allowed_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.3gp']
            if not any(audio_file.audio.name.endswith(ext) for ext in allowed_extensions):
                logger.error("Неподдерживаемый формат файла")
                return Response({"error": "Неподдерживаемый формат файла"}, status=status.HTTP_400_BAD_REQUEST)

            # Проверяем, существует ли файл
            if not os.path.exists(audio_file_path):
                logger.error(f"Файл не найден по пути: {audio_file_path}")
                return Response({"error": "Файл не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Конвертация файла в WAV, если это необходимо
            converted_file_path = audio_file_path.replace(os.path.splitext(audio_file.audio.name)[1], '.wav')
            if not audio_file.audio.name.endswith('.wav'):
                try:
                    audio = AudioSegment.from_file(audio_file_path)
                    audio.export(converted_file_path, format='wav')
                    logger.info(f"Файл конвертирован в WAV: {converted_file_path}")
                except Exception as e:
                    logger.error(f"Ошибка при конвертации файла: {str(e)}")
                    return Response({"error": "Ошибка при конвертации файла"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                model = whisper.load_model("small")  # Измените на "medium", если необходимо
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели: {str(e)}")
                return Response({"error": "Ошибка при загрузке модели"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                logger.info("Начинаю транскрибирование...")
                result = model.transcribe(converted_file_path, language='ru')  # Укажите язык
                transcribed_text = result['text']  # Получите текст

                # Извлечение вопросов
                questions = extract_questions(transcribed_text)
                logger.info(f"П: {questions}")
                for question in questions:
                    project = Project.objects.filter(ID=project_id).first()
                    if project is None:
                        logger.error(f"Проект с ID {project_id} не найден")
                        return Response({"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND)
                    Question.objects.create(Text=question, ID_Project=project)  # Сохраняем вопрос в БД
                    project.Status = True
                    project.save()

                # Возвращаем успешный ответ после успешного сохранения вопросов
                return Response({"message": "Аудио успешно загружено и обработано"}, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Ошибка при транскрибировании: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Если сериализатор не прошел валидацию, выводим ошибки
        return Response("Сохранено",status=status.HTTP_200_OK)


@api_view(['GET'])
def specialization_list(request):
    specializations = Specialization.objects.all().values('ID', 'Name')
    specializations_list = list(specializations)
    return Response(specializations_list, status=status.HTTP_200_OK)



@api_view(['GET'])
def project_list(request):
    # Получаем проекты с предзагрузкой студентов
    projects = Project.objects.all().values('ID', 'Title', 'Supervisor')
    project_list = list(projects)
    return Response(project_list, status=status.HTTP_200_OK)



@api_view(['GET'])
def commission_list(request):
    commissions = Commission.objects.all().values('ID', 'Name')
    commission_list = list(commissions)
    return Response(commission_list, status=status.HTTP_200_OK)


@api_view(['GET'])
def defense_schedule_list(request):
    commissions = DefenseSchedule.objects.all().values('ID', 'DateTime')
    commission_list = list(commissions)
    return Response(commission_list, status=status.HTTP_200_OK)


@api_view(['POST'])
def add_commission_to_schedule(request):
    try:
        commission_id = request.data.get('commissionId')
        schedule_id = request.data.get('scheduleId')

        # Найти запись в таблице DefenseSchedule по schedule_id
        defense_schedule = DefenseSchedule.objects.filter(ID=schedule_id).first()

        if not defense_schedule:
            return Response({"error": "Расписание не найдено."}, status=status.HTTP_404_NOT_FOUND)

        # Обновляем ID комиссии
        defense_schedule.ID_Commission_id = commission_id

        print(f"Saving DefenseSchedule with ID_Commission_id: {commission_id}")
        defense_schedule.save()  # Сохраняем изменения в базе данных
        print("Saved successfully")

        return Response({"message": "Комиссия успешно добавлена в расписание."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def students_by_project(request):
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
    students = Student.objects.filter(ID_Project=project_id).values('ID', 'Surname','Name', 'Patronymic')
    return Response(list(students), status=status.HTTP_200_OK)


