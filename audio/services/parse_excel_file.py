import re
from datetime import datetime
import pandas as pd
from django.db import transaction
from audio.models import Group, Student, Project, Specialization, Protocol, DefenseSchedule, Commission
import logging
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

def parse_excel_file(file_path, specialization_id, institute_id=None):
    """
    Парсит Excel-файл и сохраняет данные в базу данных, обеспечивая единичные записи для проектов и групп.
    Студенты создаются, даже если у них нет отчества (Patronymic=None).
    Поле Supervisor в Project обновляется из столбца 'Преподаватель' для каждой строки.
    Столбец 'Преподаватель' обязателен.
    Для каждого студента создаётся Protocol с ID_DefenseSchedule=None, Year=текущий год, Status=False.

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
        required_columns = ['ФИО', 'Группа', 'Тема проекта', 'Преподаватель']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Excel file is missing required columns: {', '.join(required_columns)}")
            return {"status": "error", "message": f"Missing required columns: {', '.join(required_columns)}"}

        # Проверяем существование Specialization
        try:
            specialization = Specialization.objects.get(ID=specialization_id)
            logger.debug(f"Using specialization ID: {specialization_id}")
        except Specialization.DoesNotExist:
            logger.error(f"Specialization with ID {specialization_id} not found")
            return {"status": "error", "message": f"Invalid specialization ID {specialization_id}"}

        groups_added = 0
        students_added = 0
        projects_added = 0
        projects_updated = 0
        protocols_added = 0

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
                if 'ОТЧИС' in project_title.upper():
                    logger.debug(f"Skipping row {index + 2}: Student marked as 'ОТЧИСЛЕН'")
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
                if len(fio) < 2:
                    logger.warning(f"Invalid FIO format at row {index + 2}: {row['ФИО']}")
                    continue
                surname = fio[0]
                name = fio[1]
                patronymic = " ".join(fio[2:]) if len(fio) > 2 else None

                # Извлекаем руководителя
                supervisor = str(row['Преподаватель']).strip()
                supervisor = None if not supervisor or supervisor.lower() == 'nan' else supervisor

                # Находим или создаем проект, обновляем Supervisor
                try:
                    project = Project.objects.get(Title=project_title)
                    # Обновляем Supervisor, если он отличается
                    if project.Supervisor != supervisor:
                        project.Supervisor = supervisor
                        project.save()
                        projects_updated += 1
                        logger.debug(f"Updated project Supervisor: {project_title}, Supervisor: {supervisor or 'None'}")
                except Project.DoesNotExist:
                    project = Project.objects.create(
                        Title=project_title,
                        Supervisor=supervisor,
                        Status='Защита не начата',
                        Text=''
                    )
                    projects_added += 1
                    logger.debug(f"Created project: {project_title}, Supervisor: {supervisor or 'None'}")

                # Создаем студента (уникальность по ФИО, группе и специализации)
                try:
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
                        logger.debug(f"Created student: {surname} {name} {patronymic or ''}")
                except Exception as e:
                    logger.error(f"Error creating student at row {index + 2}: {str(e)}")
                    continue

                # Обновляем связь студента с проектом, если она изменилась
                if student.ID_Project != project:
                    student.ID_Project = project
                    student.save()

                # Создаем Protocol для студента, если его ещё нет с ID_DefenseSchedule=None
                if not Protocol.objects.filter(ID_Student=student, ID_DefenseSchedule=None).exists():
                    protocol = Protocol.objects.create(
                        ID_Student=student,
                        Year=datetime.now().year,
                        Status=False,
                        Grade=None,
                        ID_Question=None,
                        ID_Question2=None,
                        DefenseStartTime=None,
                        DefenseEndTime=None,
                        Number=None
                    )
                    protocols_added += 1
                    logger.debug(f"Created Protocol for student: {student}")
                else:
                    logger.debug(f"Protocol already exists for student: {student}")

        logger.info(f"Parsed Excel: {groups_added} groups, {students_added} students, {projects_added} projects added, {projects_updated} projects updated, {protocols_added} protocols added")
        return {
            "status": "success",
            "Групп добавлено": groups_added,
            "Студентов создано": students_added,
            "Проектов добавлено": projects_added,
            "Проектов обновлено": projects_updated,
            "Протоколов добавлено": protocols_added
        }

    except Exception as e:
        logger.error(f"Error parsing Excel file: {str(e)}")
        return {"status": "error", "message": str(e)}



def parse_defense_schedule(file_path):
    """
    Парсит Excel-файл с расписанием защит, создавая записи в DefenseSchedule и обновляя существующие Protocol.
    Использует существующую Specialization, парсит даты, время и аудиторию из объединённой ячейки.
    Создаёт одну запись DefenseSchedule на временной слот, с Count равным количеству строк проектов в таблице.
    Связывает существующие протоколы с DefenseSchedule по проектам и группам, независимо от Count.
    Добавляет аудиторию в поле Class.

    Args:
        file_path (str): Путь к Excel-файлу.

    Returns:
        dict: Результат обработки (успех/ошибка, количество добавленных и связанных записей).
    """
    try:
        # Читаем все страницы Excel
        xl = pd.read_excel(file_path, sheet_name=None, header=None)

        defenses_added = 0
        protocols_linked = 0

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
                current_auditorium = None
                table_rows = []
                in_table = False

                for index, row in df.iterrows():
                    # Отладка: выводим содержимое строки
                    logger.debug(f"Row {index + 2}: {list(row)}")

                    # Пропускаем первую строку (специальность)
                    if index == 0:
                        continue

                    # Ищем строку с датой
                    row_str = str(row[0]).strip()
                    date_match = re.match(r'(\d{2}\.\d{2}\.\d{4})(?:\s*-\s*\d{2}\.\d{2}\.\d{4})?\s*-\s*[^\s]+', row_str)
                    if date_match:
                        # Если уже есть собранные строки таблицы, создаём DefenseSchedule
                        if table_rows and current_date and current_time_range:
                            slot_count = len([r for r in table_rows if r[1]])  # Count only rows with project titles
                            time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', current_time_range)
                            if time_match:
                                start_time_str, end_time_str = time_match.groups()
                                try:
                                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                                except ValueError as e:
                                    logger.error(f"Invalid time format for DefenseSchedule: {current_time_range}, error: {str(e)}")
                                    table_rows = []
                                    in_table = False
                                    continue

                                # Создаём запись DefenseSchedule с аудиторией
                                defense_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                                defense_schedule, created = DefenseSchedule.objects.get_or_create(
                                    DateTime=defense_datetime,
                                    defaults={'ID_Commission': None, 'Count': slot_count, 'Class': current_auditorium}
                                )
                                if created:
                                    defenses_added += 1
                                    logger.debug(f"Created DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")
                                else:
                                    defense_schedule.Count = slot_count
                                    defense_schedule.Class = current_auditorium
                                    defense_schedule.save()
                                    logger.debug(f"Updated DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")

                                # Связываем протоколы для всех проектов в слоте, независимо от Count
                                for group_name, project_title in table_rows:
                                    if not group_name or not project_title:
                                        continue
                                    try:
                                        group = Group.objects.get(Name=group_name.strip())
                                        project = Project.objects.get(Title=project_title.strip())
                                    except (Group.DoesNotExist, Project.DoesNotExist) as e:
                                        logger.warning(f"Group or Project not found for {group_name}, {project_title}: {str(e)}")
                                        continue

                                    students = Student.objects.filter(
                                        ID_Project=project,
                                        ID_Group=group,
                                        ID_Specialization=specialization
                                    )
                                    for student in students:
                                        protocols = Protocol.objects.filter(ID_Student=student)
                                        logger.debug(f"Found {protocols.count()} protocols for student {student}")
                                        for protocol in protocols:
                                            if protocol.ID_DefenseSchedule and protocol.ID_DefenseSchedule != defense_schedule:
                                                logger.debug(f"Skipping protocol {protocol.ID} already linked to another schedule")
                                                continue
                                            protocol.ID_DefenseSchedule = defense_schedule
                                            protocol.save()
                                            protocols_linked += 1
                                            logger.debug(f"Linked Protocol {protocol.ID} to DefenseSchedule {defense_schedule.ID} for student {student}")
                            else:
                                logger.error(f"Time range not matched for {current_time_range}")

                        # Обновляем текущую дату
                        date_str = date_match.group(1)
                        try:
                            current_date = datetime.strptime(date_str, '%d.%m.%Y')
                            logger.debug(f"Found date: {date_str}")
                            # Сохраняем предыдущие table_rows для обработки перед обновлением
                            if table_rows and current_time_range:
                                slot_count = len([r for r in table_rows if r[1]])
                                time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', current_time_range)
                                if time_match:
                                    start_time_str, end_time_str = time_match.groups()
                                    try:
                                        start_time = datetime.strptime(start_time_str, '%H:%M').time()
                                    except ValueError as e:
                                        logger.error(f"Invalid time format for DefenseSchedule: {current_time_range}, error: {str(e)}")
                                        continue
                                    defense_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                                    defense_schedule, created = DefenseSchedule.objects.get_or_create(
                                        DateTime=defense_datetime,
                                        defaults={'ID_Commission': None, 'Count': slot_count, 'Class': current_auditorium}
                                    )
                                    if created:
                                        defenses_added += 1
                                        logger.debug(f"Created DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")
                                    else:
                                        defense_schedule.Count = slot_count
                                        defense_schedule.Class = current_auditorium
                                        defense_schedule.save()
                                        logger.debug(f"Updated DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")

                                    for group_name, project_title in table_rows:
                                        if not group_name or not project_title:
                                            continue
                                        try:
                                            group = Group.objects.get(Name=group_name.strip())
                                            project = Project.objects.get(Title=project_title.strip())
                                        except (Group.DoesNotExist, Project.DoesNotExist) as e:
                                            logger.warning(f"Group or Project not found for {group_name}, {project_title}: {str(e)}")
                                            continue
                                        students = Student.objects.filter(
                                            ID_Project=project,
                                            ID_Group=group,
                                            ID_Specialization=specialization
                                        )
                                        for student in students:
                                            protocols = Protocol.objects.filter(ID_Student=student)
                                            logger.debug(f"Found {protocols.count()} protocols for student {student}")
                                            for protocol in protocols:
                                                if protocol.ID_DefenseSchedule and protocol.ID_DefenseSchedule != defense_schedule:
                                                    logger.debug(f"Skipping protocol {protocol.ID} already linked to another schedule")
                                                    continue
                                                protocol.ID_DefenseSchedule = defense_schedule
                                                protocol.save()
                                                protocols_linked += 1
                                                logger.debug(f"Linked Protocol {protocol.ID} to DefenseSchedule {defense_schedule.ID} for student {student}")
                            table_rows = []
                            current_time_range = None
                            current_auditorium = None
                            in_table = False
                        except ValueError:
                            logger.error(f"Invalid date format at row {index + 2}: {row_str}")
                        continue

                    # Ищем строку с временем (например, "13:45-17:00")
                    time_str = str(row[0]).strip() if pd.notna(row[0]) else ''
                    time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', time_str)
                    if time_match:
                        start_time_str, end_time_str = time_match.groups()
                        current_time_range = f"{start_time_str}-{end_time_str}"
                        current_auditorium = str(row[1]).strip() if pd.notna(row[1]) else None
                        logger.debug(f"Found time range: {current_time_range}, auditorium: {current_auditorium}")
                        continue

                    # Ищем заголовок таблицы
                    if row[0] == 'время' and row[1] == 'Аудитория' and row[2] == 'группа' and row[3] == 'тема проекта':
                        logger.debug(f"Found table header at row {index + 2}")
                        in_table = True
                        continue

                    # Обрабатываем строки таблицы
                    if in_table:
                        group_name = str(row[2]).strip() if pd.notna(row[2]) else ''
                        project_title = str(row[3]).strip() if pd.notna(row[3]) else ''
                        if group_name or project_title:  # Добавляем только строки с данными
                            table_rows.append((group_name, project_title))
                            logger.debug(f"Added table row: {group_name}, {project_title}")

                # Обработка последней таблицы после завершения цикла
                if table_rows and current_date and current_time_range:
                    slot_count = len([r for r in table_rows if r[1]])  # Count only rows with project titles
                    time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', current_time_range)
                    if time_match:
                        start_time_str, end_time_str = time_match.groups()
                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                        except ValueError as e:
                            logger.error(f"Invalid time format for DefenseSchedule: {current_time_range}, error: {str(e)}")
                            continue

                        # Создаём запись DefenseSchedule с аудиторией
                        defense_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                        defense_schedule, created = DefenseSchedule.objects.get_or_create(
                            DateTime=defense_datetime,
                            defaults={'ID_Commission': None, 'Count': slot_count, 'Class': current_auditorium}
                        )
                        if created:
                            defenses_added += 1
                            logger.debug(f"Created DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")
                        else:
                            defense_schedule.Count = slot_count
                            defense_schedule.Class = current_auditorium
                            defense_schedule.save()
                            logger.debug(f"Updated DefenseSchedule: {defense_datetime}, Count: {slot_count}, Class: {current_auditorium}")

                        # Связываем протоколы для всех проектов в слоте, независимо от Count
                        for group_name, project_title in table_rows:
                            if not group_name or not project_title:
                                continue
                            try:
                                group = Group.objects.get(Name=group_name.strip())
                                project = Project.objects.get(Title=project_title.strip())
                            except (Group.DoesNotExist, Project.DoesNotExist) as e:
                                logger.warning(f"Group or Project not found for {group_name}, {project_title}: {str(e)}")
                                continue

                            students = Student.objects.filter(
                                ID_Project=project,
                                ID_Group=group,
                                ID_Specialization=specialization
                            )
                            for student in students:
                                protocols = Protocol.objects.filter(ID_Student=student)
                                logger.debug(f"Found {protocols.count()} protocols for student {student}")
                                for protocol in protocols:
                                    if protocol.ID_DefenseSchedule and protocol.ID_DefenseSchedule != defense_schedule:
                                        logger.debug(f"Skipping protocol {protocol.ID} already linked to another schedule")
                                        continue
                                    protocol.ID_DefenseSchedule = defense_schedule
                                    protocol.save()
                                    protocols_linked += 1
                                    logger.debug(f"Linked Protocol {protocol.ID} to DefenseSchedule {defense_schedule.ID} for student {student}")
                    else:
                        logger.error(f"Time range not matched for {current_time_range} in final table")

        logger.info(f"Parsed defense schedule: {defenses_added} defenses added, {protocols_linked} protocols linked")
        return {
            "status": "success",
            "defenses_added": defenses_added,
            "protocols_linked": protocols_linked
        }

    except Exception as e:
        logger.error(f"Error parsing defense schedule Excel: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}