import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime
import re
import logging
from django.db import transaction
from django.utils import timezone
from sympy import false
from ..models import DefenseSchedule, Specialization, Group, Project, Student, Protocol
from django.db.models import Q


logger = logging.getLogger(__name__)

def get_next_protocol_number(specialization, year):
    """
    Возвращает следующий порядковый номер для специальности и года.
    """
    protocols = Protocol.objects.filter(
        ID_Student__ID_Specialization=specialization,
        Year=year
    ).exclude(Number='').exclude(Number__isnull=True)

    if not protocols.exists():
        return 1

    max_seq = 0
    for p in protocols:
        # Берём цифры в начале строки
        match = re.match(r'^(\d+)', p.Number)
        if match:
            seq = int(match.group(1))
            if seq > max_seq:
                max_seq = seq

    return max_seq + 1

def parse_excel_file(file_path, specialization_id, institute_id=None):
    """
    Парсит Excel-файл и сохраняет данные в базу данных, обеспечивая единичные записи для проектов и групп.
    Студенты создаются, даже если у них нет отчества (Patronymic=None).
    Поле Supervisor в Project обновляется из столбца 'Преподаватель' или 'Руководитель' для каждой строки.
    Один из столбцов 'Преподаватель' или 'Руководитель' обязателен.
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

        # Проверяем наличие необходимых колонок (ФИО, Группа, Тема проекта + один из: Преподаватель/Руководитель)
        required_columns = ['ФИО', 'Группа', 'Тема проекта']
        supervisor_column = None
        
        # Проверяем, какая из колонок руководителя присутствует
        if 'Преподаватель' in df.columns:
            supervisor_column = 'Преподаватель'
        elif 'Руководитель' in df.columns:
            supervisor_column = 'Руководитель'
        else:
            return {"status": "error", "message": "Отсутствует обязательный столбец: 'Преподаватель' или 'Руководитель'"}
        
        # Проверяем остальные обязательные колонки
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            return {"status": "error", "message": f"Отсутствуют обязательные столбцы: {', '.join(missing)}"}

        # Проверяем существование Specialization
        try:
            specialization = Specialization.objects.get(ID=specialization_id)
        except Specialization.DoesNotExist:
            return {"status": "error", "message": f"Неверный ID направления: {specialization_id}"}

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
                    continue

                # Проверяем тему проекта
                project_title = str(row.get('Тема проекта', '')).strip()
                if not project_title or project_title.lower() == 'nan':
                    continue

                # Пропускаем отчисленных студентов
                if 'ОТЧИС' in project_title.upper():
                    continue

                # Извлекаем название группы
                group_name = str(row['Группа']).strip()

                # Проверка существования группы
                if Group.objects.filter(Name=group_name).exists():
                    group = Group.objects.get(Name=group_name)
                else:
                    group = Group.objects.create(Name=group_name)
                    groups_added += 1
                
                # Парсим ФИО
                fio = str(row['ФИО']).strip().split()
                if len(fio) < 2:
                    continue
                surname = fio[0]
                name = fio[1]
                patronymic = " ".join(fio[2:]) if len(fio) > 2 else None

                # Извлекаем руководителя из нужной колонки
                supervisor = str(row.get(supervisor_column, '')).strip()
                supervisor = None if not supervisor or supervisor.lower() == 'nan' else supervisor

                # Находим или создаем проект, обновляем Supervisor
                try:
                    project = Project.objects.get(Title=project_title)
                    # Обновляем Supervisor, если он отличается
                    if project.Supervisor != supervisor:
                        project.Supervisor = supervisor
                        project.save()
                        projects_updated += 1
                except Project.DoesNotExist:
                    project = Project.objects.create(
                        Title=project_title,
                        Supervisor=supervisor,
                        Status='Защита не начата'
                    )
                    projects_added += 1

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
                except Exception as e:
                    logger.error(f"Ошибка при создании студента в строке {index + 2}: {str(e)}")
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
                        Number=''
                    )
                    protocols_added += 1

        return {
            "status": "success",
            "Групп добавлено": groups_added,
            "Студентов создано": students_added,
            "Проектов добавлено": projects_added,
            "Проектов обновлено": projects_updated,
            "Протоколов добавлено": protocols_added
        }

    except Exception as e:
        return {"status": "error", "message": f"Ошибка при обработке файла: {str(e)}"}


def parse_defense_schedule(file_path, specialization_id):
    """
    Парсит Excel-файл с расписанием защит, создавая новые записи в DefenseSchedule и обновляя существующие Protocol.
    Использует существующую Specialization, парсит даты, время и аудиторию из объединённой ячейки.
    Создаёт новую запись DefenseSchedule на временной слот, с Count равным количеству строк, объединённых в столбце B (аудитория).
    Обновляет существующие протоколы, привязывая их к новому DefenseSchedule, даже если они уже связаны с другим.
    Добавляет аудиторию в поле Class. Извлекает все проекты из столбца D в пределах объединённых строк.
    Args:
        file_path (str): Путь к Excel-файлу.

    Returns:
        dict: Результат обработки (успех/ошибка, количество добавленных и связанных записей).
    """
    try:
        # Загружаем Excel-файл с помощью openpyxl
        workbook = openpyxl.load_workbook(file_path, data_only=True)

        defenses_added = 0
        protocols_linked = 0
        try:
            specialization = Specialization.objects.get(ID=specialization_id)
        except Specialization.DoesNotExist:
            return {"status": "error", "message": "Специальность не найдена"}
        
        with transaction.atomic():
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]

                # Парсим строки для поиска дат и таблиц
                current_date = None
                current_time_range = None
                current_auditorium = None
                table_rows = []
                in_table = False
                merged_row_count = 0
                table_start_row = None
                time_row_found = False

                # Проходим по строкам листа
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    # Ищем строку с датой
                    row_str = str(row[0]).strip() if row[0] else ''
                    date_match = re.match(r'(\d{2}\.\d{2}\.\d{4})(?:\s*-\s*\d{2}\.\d{2}\.\d{4})?\s*-\s*[^\s]+', row_str)
                    if date_match:
                        # Если уже есть собранные строки таблицы, создаём DefenseSchedule
                        if table_rows and current_date and current_time_range:
                            slot_count = merged_row_count  # Количество объединённых строк в столбце B
                            time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', current_time_range)
                            if time_match:
                                start_time_str, end_time_str = time_match.groups()
                                try:
                                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                                except ValueError as e:
                                    table_rows = []
                                    merged_row_count = 0
                                    in_table = False
                                    table_start_row = None
                                    time_row_found = False
                                    continue

                                # Создаём новую запись DefenseSchedule
                                defense_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                                defense_schedule = DefenseSchedule.objects.create(
                                    DateTime=defense_datetime,
                                    ID_Commission=None,
                                    ID_Specialization=specialization,  
                                    Count=slot_count,
                                    Class=current_auditorium
                                )
                                defenses_added += 1

                                # Связываем протоколы для всех проектов в слоте, обновляя существующие
                                for group_name, project_title in table_rows:
                                    if not group_name or not project_title:
                                        continue
                                    try:
                                        group = Group.objects.get(Name=str(group_name).strip())
                                        project = Project.objects.get(Title=str(project_title).strip())
                                    except (Group.DoesNotExist, Project.DoesNotExist) as e:
                                        continue

                                    students = Student.objects.filter(
                                        ID_Project=project,
                                        ID_Group=group,
                                        ID_Specialization=specialization
                                    )
                                    for student in students:
                                        protocols = Protocol.objects.filter(ID_Student=student)
                                        for protocol in protocols:
                                            protocol.ID_DefenseSchedule = defense_schedule  # Обновляем связь
                                            protocol.save()
                                            protocols_linked += 1

                        # Обновляем текущую дату
                        date_str = date_match.group(1)
                        try:
                            current_date = datetime.strptime(date_str, '%d.%m.%Y')
                            table_rows = []
                            merged_row_count = 0
                            current_time_range = None
                            current_auditorium = None
                            in_table = False
                            table_start_row = None
                            time_row_found = False
                        except ValueError:
                            logger.error(f"Invalid date format at row {row_idx}: {row_str}")
                        continue

                    # Ищем заголовок таблицы
                    if row[0] == 'Время' and row[1] == 'Аудитория' and row[2] == 'Группа' and row[3] == 'Тема проекта':
                        in_table = True
                        table_start_row = row_idx + 1  # Следующая строка после заголовка
                        continue

                    # Ищем строку с временем и извлекаем проект
                    if in_table and row_idx == table_start_row and not time_row_found:
                        time_str = str(row[0]).strip() if row[0] else ''
                        time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', time_str)
                        if time_match:
                            start_time_str, end_time_str = time_match.groups()
                            current_time_range = f"{start_time_str}-{end_time_str}"
                            current_auditorium = str(row[1]).strip() if row[1] else None

                            # Извлекаем группу и проект из строки с временем
                            group_name = str(row[2]).strip() if row[2] else ''
                            project_title = str(row[3]).strip() if row[3] else ''
                            if project_title:  # Добавляем только если есть проект
                                table_rows.append((group_name, project_title))

                            # Определяем количество объединённых строк в столбце B
                            merged_row_count = 0
                            for merged_range in sheet.merged_cells.ranges:
                                if merged_range.min_col == 2 and merged_range.max_col == 2:
                                    if merged_range.min_row == row_idx:
                                        merged_row_count = merged_range.max_row - merged_range.min_row + 1
                                        break
                            if merged_row_count == 0:
                                merged_row_count = 1
                            time_row_found = True
                            table_start_row = row_idx + 1  # Данные начинаются со следующей строки
                            continue

                    # Обрабатываем все строки таблицы в пределах merged_row_count
                    if in_table and row_idx >= table_start_row and row_idx < table_start_row + merged_row_count:
                        group_name = str(row[2]).strip() if row[2] else ''
                        project_title = str(row[3]).strip() if row[3] else ''
                        if project_title:  # Добавляем только если есть проект
                            table_rows.append((group_name, project_title))
                    elif in_table and row_idx >= table_start_row + merged_row_count:
                        in_table = False
                        table_start_row = None
                        time_row_found = False

                # Обработка последней таблицы после завершения цикла
                if current_date and current_time_range:
                    slot_count = merged_row_count  # Количество объединённых строк в столбце B
                    time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', current_time_range)
                    if time_match:
                        start_time_str, end_time_str = time_match.groups()
                        try:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                        except ValueError as e:
                            continue

                        # Создаём новую запись DefenseSchedule
                        defense_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                        defense_schedule = DefenseSchedule.objects.create(
                            DateTime=defense_datetime,
                            ID_Commission=None,
                            Count=slot_count,
                            Class=current_auditorium
                        )
                        defenses_added += 1

                        # Связываем протоколы для всех проектов в слоте, обновляя существующие
                        for group_name, project_title in table_rows:
                            if not group_name or not project_title:
                                continue
                            try:
                                group = Group.objects.get(Name=str(group_name).strip())
                                project = Project.objects.get(Title=str(project_title).strip())
                            except (Group.DoesNotExist, Project.DoesNotExist) as e:
                                continue

                            students = Student.objects.filter(
                                ID_Project=project,
                                ID_Group=group,
                                ID_Specialization=specialization
                            )
                            for student in students:
                                protocols = Protocol.objects.filter(ID_Student=student, Status=false)
                                for protocol in protocols:
                                    protocol.ID_DefenseSchedule = defense_schedule  # Обновляем связь
                                    protocol.save()
                                    protocols_linked += 1

        return {
            "status": "success",
            "defenses_added": defenses_added,
            "protocols_linked": protocols_linked
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}