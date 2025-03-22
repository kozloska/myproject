# audio/views.py
import os
import logging
from datetime import datetime

from django.contrib.auth.hashers import check_password
from django.core.files.storage import default_storage
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Specialization, Commission, DefenseSchedule, Project, Student, SecretarySpecialization, Question, \
    CommissionComposition, CommissionMember, User
from .serializers import AudioFileSerializer, ProjectSerializer
import whisper
from pydub import AudioSegment
import spacy
from .models import Specialization, Student, Project

# Настройка логгера
logger = logging.getLogger(__name__)
print(whisper.__version__)

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
            allowed_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.3gp', '.m4a']

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
def specialization_list_by_secretary(request):
    secretary_id = request.query_params.get('secretary_id')
    specializations = SecretarySpecialization.objects.filter(ID_Secretary_id=secretary_id).values('ID_Specialization_id')
    # Получаем список ID специализаций
    specialization_ids = [spec['ID_Specialization_id'] for spec in specializations]
    # Получаем специализации по ID
    specializations_list = Specialization.objects.filter(ID__in=specialization_ids).values('ID', 'Name')
    return Response(list(specializations_list), status=status.HTTP_200_OK)


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
def commission_list_by_member(request):
    member_id = request.query_params.get('secretary_id')
    # Получаем комиссии, в которых есть указанный член комиссии
    commissions = Commission.objects.filter(
        commissioncomposition__ID_Member=member_id,
        commissioncomposition__Role='Секретарь'
    ).values('ID', 'Name')  # Извлекаем ID и Name
    if not commissions:
        return Response(
            {'message': 'Комиссии не найдены для данного члена комиссии.'},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(commissions, status=status.HTTP_200_OK)


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

        defense_schedule.save()  # Сохраняем изменения в базе данных

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



@api_view(['GET'])
def questions_by_project(request):
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


@api_view(['POST'])
def authorize_user(request):
    surname = request.data.get('surname')
    name = request.data.get('name')
    patronymic = request.data.get('patronymic')

    # Ищем пользователя в базе данных по ФИО
    try:
        user = CommissionMember.objects.get(
            Surname=surname,
            Name=name,
            Patronymic=patronymic
        )
    except CommissionMember.DoesNotExist:
        return Response( {'message': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

    # Возвращаем информацию об авторизованном пользователе
    return Response({
        'id': user.ID
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_projects_by_defense_schedule_and_specialization(request):
    defense_schedule_id = request.query_params.get('defense_schedule_id')
    specialization_id = request.query_params.get('specialization_id')
    try:
        projects = Project.objects.filter(
            student__id_defense_schedule__id=defense_schedule_id,
            student__id_specialization=specialization_id
        ).prefetch_related(
            Prefetch('student', queryset=Student.objects.select_related('id_defense_schedule', 'id_specialization'))
        ).values('id', 'title', 'supervisor')

        return Response(list(projects), status=status.HTTP_200_OK)
    except (Project.DoesNotExist, Student.DoesNotExist, Specialization.DoesNotExist, DefenseSchedule.DoesNotExist):
        return Response({'message': 'Проекты не найдены.'}, status=status.HTTP_404_NOT_FOUND)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Question, Project


@api_view(['PUT'])
def update_question(request):
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


@api_view(['DELETE'])
def delete_question(request):
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


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Student, Protocol


@api_view(['POST'])
def update_grade(request):
    try:
        # Получаем данные из тела запроса
        student_id = request.query_params.get('student_id')
        grade = request.query_params.get('grade')

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


@api_view(['POST'])
def create_question(request):
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



@api_view(['GET'])
def get_today_defenses_by_specialization(request):
    specialization_id = request.query_params.get('specialization_id')
    date_str  = request.query_params.get('today')
    try:
        # Получаем направление по ID
        specialization = Specialization.objects.get(ID=specialization_id)

        # Преобразуем строку даты в объект datetime
        defense_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Получаем расписания защит через протокол
        defenses = DefenseSchedule.objects.filter(
            protocol__ID_Student__ID_Specialization=specialization,
            DateTime__date=defense_date
        ).distinct()

        # Формируем ответ
        response_data = [
            {'ID': defense.ID, 'DateTime': defense.DateTime}
            for defense in defenses
        ]

        return Response(response_data, status=status.HTTP_200_OK)

    except Specialization.DoesNotExist:
        return Response({'error': 'Specialization not found'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_commission_composition(request):
    id_commission = request.data.get('id_commission')
    # Получаем состав комиссии по ID
    compositions = CommissionComposition.objects.filter(ID_Commission_id=id_commission).select_related('ID_Member')

    # Формируем список членов комиссии
    members_list = []
    for composition in compositions:
        member = {
            'ID': composition.ID_Member.ID,
            'Surname': composition.ID_Member.Surname,
            'Name': composition.ID_Member.Name,
            'Patronymic': composition.ID_Member.Patronymic,
            'Role': composition.Role,
        }
        members_list.append(member)
    return Response(members_list, status=status.HTTP_200_OK)


@api_view(['POST'])
def authenticate_user(request):
    login = request.data.get('login')
    password = request.data.get('password')

    try:
        user = User.objects.get(login=login)
        if user.password == password:  # Сравнение пароля без шифрования
            return Response({'full_name': user.full_name}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Неверный пароль'}, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def project_list_by_defense_schedule_id(request):
    defense_schedule_id = request.query_params.get('defense_schedule_id')

    projects = Project.objects.filter(
        ID__in=Protocol.objects.filter(
            ID_DefenseSchedule=defense_schedule_id
        ).values('ID_Student__ID_Project')
    ).values('ID', 'Title', 'Supervisor')

    project_list = list(projects)
    return Response(project_list, status=status.HTTP_200_OK)