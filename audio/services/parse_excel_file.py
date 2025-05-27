import re
from datetime import datetime

import pandas as pd
from django.db import transaction
from audio.models import Group, Student, Project, Specialization, Protocol, DefenseSchedule, Commission
import logging

logger = logging.getLogger(__name__)

def parse_excel_file(file_path, specialization_id, institute_id=None):
    """
    Парсит Excel-файл и сохраняет данные в базу данных, обеспечивая единичные записи для проектов и групп.
    Студенты создаются только если указана непустая тема проекта.
    Проверяет существование группы перед созданием.

    Args:
        file_path (str): Путь к Excel-файлу.
        specialization_id (int): ID направления (Specialization).
        institute_id (int, optional): Не используется в текущей версии, но сохранен для совместимости.

    Returns:
        dict: Результат обработки (успех/ошибка, количество добавленных записей).
    """
    try:
        # Читаем Excel-файл
        df = pd.read_excel(file_path, sheet_name=0)

        # Проверяем наличие необходимых колонок
        required_columns = ['ФИО', 'Группа', 'Тема проекта']
        if not all(col in df.columns for col in required_columns):
            logger.error("Excel file is missing required columns")
            return {"status": "error", "message": "Missing required columns in Excel file"}

        # Проверяем существование Specialization
        try:
            specialization = Specialization.objects.get(ID=specialization_id)
        except Specialization.DoesNotExist:
            logger.error(f"Specialization with ID {specialization_id} not found")
            return {"status": "error", "message": f"Specialization with ID {specialization_id} not found"}

        groups_added = 0
        students_added = 0
        projects_added = 0

        # Атомарная транзакция для целостности данных
        with transaction.atomic():
            for index, row in df.iterrows():
                # Пропускаем строки с пустыми ФИО или Группа
                if pd.isna(row['ФИО']) or pd.isna(row['Группа']):
                    logger.debug(f"Skipping row {index + 2}: Empty ФИО or Группа")
                    continue

                # Проверяем тему проекта
                project_title = str(row.get('Тема проекта', '')).strip()
                if not project_title or project_title.lower() == 'nan':
                    logger.debug(f"Skipping row {index + 2}: Empty project title")
                    continue

                # Пропускаем отчисленных студентов
                if 'ОТЧИСЛЕН' in project_title.upper():
                    logger.debug(f"Skipping row {index + 2}: Student marked as ОТЧИСЛЕН")
                    continue

                # Извлекаем название группы
                group_name = str(row['Группа']).strip()

                # Явная проверка существования группы
                if Group.objects.filter(Name=group_name).exists():
                    logger.info(f"Group '{group_name}' already exists, using existing record")
                    group = Group.objects.get(Name=group_name)
                else:
                    group = Group.objects.create(Name=group_name)
                    groups_added += 1
                    logger.debug(f"Created group: {group_name}")

                # Парсим ФИО
                fio = str(row['ФИО']).strip().split()
                if len(fio) < 3:
                    logger.warning(f"Invalid FIO format at row {index + 2}: {row['ФИО']}")
                    continue
                surname, name, patronymic = fio[0], fio[1], " ".join(fio[2:])

                # Создаем проект (единичная запись для одинаковых тем)
                supervisor = str(row.get('Преподаватель', 'Unknown')).strip()
                project, created = Project.objects.get_or_create(
                    Title=project_title,
                    defaults={
                        'Supervisor': supervisor,
                        'Status': 'Защита не начата',
                        'Text': ''
                    }
                )
                if created:
                    projects_added += 1
                    logger.debug(f"Created project: {project_title}")

                # Создаем студента (уникальность по ФИО, группе и специализации)
                student, created = Student.objects.get_or_create(
                    Surname=surname,
                    Name=name,
                    Patronymic=patronymic,
                    ID_Group=group,
                    ID_Specialization=specialization,
                    defaults={'ID_Project': project}
                )
                if created:
                    students_added += 1
                    logger.debug(f"Created student: {surname} {name} {patronymic}")

                # Обновляем связь студента с проектом, если она изменилась
                if student.ID_Project != project:
                    student.ID_Project = project
                    student.save()

        logger.info(f"Parsed Excel: {groups_added} groups, {students_added} students, {projects_added} projects added")
        return {
            "status": "success",
            "groups_added": groups_added,
            "students_added": students_added,
            "projects_added": projects_added
        }

    except Exception as e:
        logger.error(f"Error parsing Excel file: {str(e)}")
        return {"status": "error", "message": str(e)}



def parse_schedule_excel(file_path, specialization_id=None):
    """
    Парсит Excel-файл с расписанием защит, создавая записи в DefenseSchedule и Protocol.
    Каждая страница содержит специальность в первой строке и расписание защит.

    Args:
        file_path (str): Путь к Excel-файлу.
        specialization_id (int, optional): ID направления (не используется, специальность из файла).

    Returns:
        dict: Результат обработки (успех/ошибка, количество добавленных записей).
    """
    try:
        # Читаем все страницы Excel
        xl = pd.read_excel(file_path, sheet_name=None, header=None)

        defenses_added = 0
        protocols_added = 0

        with transaction.atomic():
            for sheet_name, df in xl.items():
                logger.info(f"Processing sheet: {sheet_name}")

                # Первая строка — название специальности
                if df.empty or len(df) < 1:
                    logger.warning(f"Sheet {sheet_name} is empty")
                    continue
                specialization_name = str(df.iloc[0, 0]).strip()
                if not specialization_name or specialization_name.lower() == 'nan':
                    logger.error(f"No specialization name found in sheet {sheet_name}")
                    continue

                # Находим или создаём Specialization
                specialization, _ = Specialization.objects.get_or_create(
                    Name=specialization_name,
                    defaults={'Qualification': 'Unknown'}
                )
                logger.debug(f"Using specialization: {specialization_name}")

                # Парсим строки для поиска дат и таблиц
                current_date = None
                current_commission = None
                current_time_range = None
                for index, row in df.iterrows():
                    # Пропускаем первую строку (специальность)
                    if index == 0:
                        continue

                    # Ищем дату и комиссию (например, "15.05.2025 - ГЭК_2")
                    row_str = str(row[0]).strip()
                    date_match = re.match(r'(\d{2}\.\d{2}\.\d{4})\s*-\s*([^\s]+)', row_str)
                    if date_match:
                        date_str, commission_name = date_match.groups()
                        try:
                            current_date = datetime.strptime(date_str, '%d.%m.%Y')
                        except ValueError:
                            logger.error(f"Invalid date format at row {index + 2}: {row_str}")
                            continue

                        # Находим или создаём Commission
                        current_commission, _ = Commission.objects.get_or_create(
                            Name=commission_name,
                            ID_Specialization=specialization
                        )
                        logger.debug(f"Using commission: {commission_name}")
                        continue

                    # Ищем строку с заголовком таблицы
                    if row[0] == 'время' and row[1] == 'Аудитория' and row[2] == 'группа' and row[3] == 'тема проекта':
                        continue

                    # Парсим время
                    time_str = str(row[0]).strip() if pd.notna(row[0]) else ''
                    if time_str and '-' in time_str:
                        current_time_range = time_str
                        continue

                    # Обрабатываем строки таблицы
                    if pd.isna(row[0]) and pd.notna(row[2]) and pd.notna(row[3]):
                        group_name = str(row[2]).strip()
                        project_title = str(row[3]).strip()

                        if not group_name or not project_title:
                            logger.debug(f"Skipping row {index + 2}: Empty group or project title")
                            continue

                        # Пропускаем пересдачи
                        if 'пересдача' in str(row[0]).lower() or 'пересдача' in str(row[3]).lower():
                            logger.debug(f"Skipping row {index + 2}: Marked as пересдача")
                            continue

                        # Находим или создаём Group
                        group, _ = Group.objects.get_or_create(Name=group_name)
                        logger.debug(f"Using group: {group_name}")

                        # Находим Project
                        try:
                            project = Project.objects.get(Title=project_title)
                        except Project.DoesNotExist:
                            logger.warning(f"Project '{project_title}' not found at row {index + 2}")
                            continue

                        # Парсим время защиты
                        if not current_time_range:
                            logger.error(f"No time range specified for row {index + 2}")
                            continue

                        start_time_str, end_time_str = None, None
                        time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})(?:\s*\(с\s*(\d{2}:\d{2})\))?', current_time_range)
                        if time_match:
                            start_time_str, end_time_str, specific_start = time_match.groups()
                            if specific_start:
                                start_time_str = specific_start
                        else:
                            logger.error(f"Invalid time format at row {index + 2}: {current_time_range}")
                            continue

                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                            end_time = datetime.strptime(end_time_str, '%H:%M').time()
                        except ValueError:
                            logger.error(f"Invalid time format at row {index + 2}: {current_time_range}")
                            continue

                        # Создаём DefenseSchedule
                        if not current_date or not current_commission:
                            logger.error(f"Missing date or commission for row {index + 2}")
                            continue

                        defense_datetime = datetime.combine(current_date.date(), start_time)
                        defense_schedule, created = DefenseSchedule.objects.get_or_create(
                            DateTime=defense_datetime,
                            ID_Commission=current_commission
                        )
                        if created:
                            defenses_added += 1
                            logger.debug(f"Created DefenseSchedule: {defense_datetime}")

                        # Находим студентов
                        students = Student.objects.filter(
                            ID_Project=project,
                            ID_Group=group,
                            ID_Specialization=specialization
                        )
                        if not students.exists():
                            logger.warning(f"No students found for project '{project_title}' in group '{group_name}'")
                            continue

                        # Создаём Protocol для каждого студента
                        for student in students:
                            protocol, created = Protocol.objects.get_or_create(
                                ID_Student=student,
                                ID_DefenseSchedule=defense_schedule,
                                defaults={
                                    'Year': 2025,
                                    'Grade': 'Не определена',
                                    'ID_Question': None,
                                    'ID_Question2': None,
                                    'DefenseStartTime': start_time,
                                    'DefenseEndTime': end_time,
                                    'Number': f'P{student.ID}-{defense_schedule.ID}',
                                    'Status': False
                                }
                            )
                            if created:
                                protocols_added += 1
                                logger.debug(f"Created Protocol for student: {student}")

        logger.info(f"Parsed schedule: {defenses_added} defenses, {protocols_added} protocols added")
        return {
            "status": "success",
            "defenses_added": defenses_added,
            "protocols_added": protocols_added
        }

    except Exception as e:
        logger.error(f"Error parsing schedule Excel: {str(e)}")
        return {"status": "error", "message": str(e)}

def parse_defense_schedule(file_path):
    """
    Парсит Excel-файл с расписанием защит, создавая записи в DefenseSchedule и Protocol.
    Использует существующую Specialization, парсит даты и общее время, не трогает DefenseStartTime, DefenseEndTime и Commission.
    Не создаёт Specialization и Project, только использует существующие.

    Args:
        file_path (str): Путь к Excel-файлу.

    Returns:
        dict: Результат обработки (успех/ошибка, количество добавленных записей).
    """
    try:
        # Читаем все страницы Excel
        xl = pd.read_excel(file_path, sheet_name=None, header=None)

        defenses_added = 0
        protocols_added = 0

        with transaction.atomic():
            for sheet_name, df in xl.items():
                logger.info(f"Processing sheet: {sheet_name}")

                # Первая строка — название специальности
                if df.empty or len(df) < 1:
                    logger.warning(f"Sheet {sheet_name} is empty")
                    continue
                specialization_name = str(df.iloc[0, 0]).strip()
                if not specialization_name or specialization_name.lower() == 'nan':
                    logger.error(f"No specialization name found in sheet {sheet_name}")
                    continue

                # Находим существующую Specialization
                try:
                    specialization = Specialization.objects.get(Name=specialization_name)
                except Specialization.DoesNotExist:
                    logger.error(f"Specialization '{specialization_name}' not found in database")
                    continue
                logger.debug(f"Using specialization: {specialization_name}")

                # Парсим строки для поиска дат и таблиц
                current_date = None
                current_time_range = None
                skip_next = False  # Флаг для пропуска строки заголовков

                for index, row in df.iterrows():
                    # Отладка: выводим содержимое строки
                    logger.debug(f"Row {index + 2}: {list(row)}")

                    # Пропускаем первую строку (специальность)
                    if index == 0:
                        continue

                    # Пропускаем строку заголовков после даты
                    if skip_next:
                        if row[0] == 'время' and row[1] == 'Аудитория' and row[2] == 'группа' and row[3] == 'тема проекта':
                            logger.debug(f"Found table header at row {index + 2}")
                        skip_next = False
                        continue

                    # Ищем строку с датой
                    row_str = str(row[0]).strip()
                    date_match = re.match(r'(\d{2}\.\d{2}\.\d{4})(?:\s*-\s*\d{2}\.\d{2}\.\d{4})?\s*-\s*[^\s]+', row_str)
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            current_date = datetime.strptime(date_str, '%d.%m.%Y')
                            logger.debug(f"Found date: {date_str}")
                            skip_next = True  # Следующая строка — заголовки
                        except ValueError:
                            logger.error(f"Invalid date format at row {index + 2}: {row_str}")
                            continue
                        continue

                    # Ищем строку с временем
                    time_str = str(row[0]).strip() if pd.notna(row[0]) else ''
                    time_match = re.match(r'(\d{2}:\d{2}(?::\d{2})?)\s*-\s*(\d{2}:\d{2}(?::\d{2})?)', time_str)
                    if time_match:
                        current_time_range = time_str
                        logger.debug(f"Found time range: {time_str}")
                        continue

                    # Ищем заголовок таблицы
                    if row[0] == 'время' and row[1] == 'Аудитория' and row[2] == 'группа' and row[3] == 'тема проекта':
                        logger.debug(f"Found table header at row {index + 2}")
                        continue

                    # Обрабатываем строки таблицы
                    if pd.isna(row[0]) and pd.notna(row[2]) and pd.notna(row[3]):
                        group_name = str(row[2]).strip()
                        project_title = str(row[3]).strip()

                        if not group_name or not project_title:
                            logger.debug(f"Skipping row {index + 2}: Empty group or project title")
                            continue

                        # Пропускаем пересдачи
                        if 'пересдача' in str(row[0]).lower() or 'пересдача' in str(row[3]).lower():
                            logger.debug(f"Skipping row {index + 2}: Marked as пересдача")
                            continue

                        # Находим или создаём Group
                        group, created = Group.objects.get_or_create(Name=group_name)
                        if created:
                            logger.debug(f"Created group: {group_name}")
                        logger.debug(f"Using group: {group_name}")

                        # Находим существующий Project
                        try:
                            project = Project.objects.get(Title=project_title)
                        except Project.DoesNotExist:
                            logger.warning(f"Project '{project_title}' not found at row {index + 2}")
                            continue

                        # Проверяем наличие даты и времени
                        if not current_time_range or not current_date:
                            logger.error(f"No time range or date specified for row {index + 2}")
                            continue

                        # Парсим время
                        time_match = re.match(r'(\d{2}:\d{2}(?::\d{2})?)\s*-\s*(\d{2}:\d{2}(?::\d{2})?)', current_time_range)
                        if not time_match:
                            logger.error(f"Invalid time format at row {index + 2}: {current_time_range}")
                            continue

                        start_time_str, end_time_str = time_match.groups()
                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                            end_time = datetime.strptime(end_time_str, '%H:%M').time()
                        except ValueError:
                            try:
                                start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
                                end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
                            except ValueError:
                                logger.error(f"Invalid time format at row {index + 2}: {current_time_range}")
                                continue

                        # Создаём DefenseSchedule без комиссии
                        defense_datetime = datetime.combine(current_date.date(), start_time)
                        defense_schedule, created = DefenseSchedule.objects.get_or_create(
                            DateTime=defense_datetime,
                            defaults={'ID_Commission': None}
                        )
                        if created:
                            defenses_added += 1
                            logger.debug(f"Created DefenseSchedule: {defense_datetime}")

                        # Находим студентов
                        students = Student.objects.filter(
                            ID_Project=project,
                            ID_Group=group,
                            ID_Specialization=specialization
                        )
                        if not students.exists():
                            logger.warning(f"No students found for project '{project_title}' in group '{group_name}'")
                            continue

                        # Создаём Protocol для каждого студента
                        for student in students:
                            protocol, created = Protocol.objects.get_or_create(
                                ID_Student=student,
                                ID_DefenseSchedule=defense_schedule,
                                defaults={
                                    'Year': None,
                                    'Grade': 'Не определена',
                                    'ID_Question': None,
                                    'ID_Question2': None,
                                    'DefenseStartTime': None,
                                    'DefenseEndTime': None,
                                    'Number': None,
                                    'Status': False
                                }
                            )
                            if created:
                                protocols_added += 1
                                logger.debug(f"Created Protocol for student: {student}")

        logger.info(f"Parsed defense schedule: {defenses_added} defenses, {protocols_added} protocols added")
        return {
            "status": "success",
            "defenses_added": defenses_added,
            "protocols_added": protocols_added
        }

    except Exception as e:
        logger.error(f"Error parsing defense schedule Excel: {str(e)}")
        return {"status": "error", "message": str(e)}