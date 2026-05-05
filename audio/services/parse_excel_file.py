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
    print(f"=== НАЧАЛО ПАРСИНГА === Файл: {file_path}, Specialization ID: {specialization_id}")
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
                            Class=current_auditorium,
                            ID_Specialization = specialization

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
                                protocols = Protocol.objects.filter(ID_Student=student, Status=False)
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
    


def parse_defense_schedule(file_path, specialization_id):
    print(f"\n=== 🔧 НАЧАЛО ПАРСИНГА (с поддержкой пустых слотов) ===")
    print(f"📁 Файл: {file_path}, Spec ID: {specialization_id}")
    
    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        print(f"📑 Листы: {workbook.sheetnames}")

        defenses_added = 0
        protocols_linked = 0
        
        try:
            specialization = Specialization.objects.get(ID=specialization_id)
            print(f"✅ Specialization: {specialization.Name}")
        except Specialization.DoesNotExist:
            print(f"❌ Specialization не найдена!")
            return {"status": "error", "message": "Специальность не найдена"}
        
        with transaction.atomic():
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                print(f"\n--- Лист: '{sheet_name}', строк: {sheet.max_row} ---")

                current_date = None
                # Текущий накапливаемый слот
                current_slot = {
                    'time': None,
                    'auditorium': None,
                    'count': 0,      # Количество выделенных мест (из merged cells)
                    'students': []   # Список найденных студентов (Group, Project)
                }
                
                def save_slot(slot, date):
                    """Сохраняет слот в БД, даже если он пустой"""
                    nonlocal defenses_added, protocols_linked
                    
                    if not date or not slot['time']:
                        print(f"⚠️ Пропуск: нет даты или времени")
                        return

                    print(f"💾 СОХРАНЕНИЕ СЛОТА: {date.date()} {slot['time']}, Ауд:{slot['auditorium']}, Мест:{slot['count']}, Студентов:{len(slot['students'])}")
                    
                    time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', slot['time'])
                    if not time_match:
                        print(f"❌ Ошибка формата времени: {slot['time']}")
                        return

                    try:
                        start_time = datetime.strptime(time_match.group(1), '%H:%M').time()
                    except ValueError:
                        print(f"❌ Ошибка парсинга времени")
                        return

                    defense_dt = timezone.make_aware(datetime.combine(date, start_time))
                    
                    # Создаем запись расписания ВСЕГДА, даже если students пуст
                    defense = DefenseSchedule.objects.create(
                        DateTime=defense_dt,
                        ID_Specialization=specialization,
                        Count=slot['count'], # Берем count из объединенных ячеек
                        Class=slot['auditorium']
                    )
                    defenses_added += 1
                    print(f"✅ Создан DefenseSchedule ID={defense.ID} (Count={slot['count']})")

                    # Привязываем студентов, если они есть
                    for group_name, project_title in slot['students']:
                        if not group_name or not project_title:
                            continue
                        
                        group_name = str(group_name).strip()
                        project_title = str(project_title).strip()

                        try:
                            group = Group.objects.get(Name=group_name)
                            project = Project.objects.get(Title=project_title)
                        except (Group.DoesNotExist, Project.DoesNotExist):
                            print(f"   ⚠️ НЕ найдено в БД: '{group_name}' / '{project_title[:30]}'")
                            continue

                        students = Student.objects.filter(
                            ID_Project=project, 
                            ID_Group=group, 
                            ID_Specialization=specialization
                        )
                        
                        for student in students:
                            protocol = Protocol.objects.filter(ID_Student=student, ID_DefenseSchedule=None).first()
                            if protocol:
                                protocol.ID_DefenseSchedule = defense
                                protocol.save(update_fields=['ID_DefenseSchedule'])
                                protocols_linked += 1
                            else:
                                Protocol.objects.create(
                                    ID_Student=student, 
                                    ID_DefenseSchedule=defense,
                                    Year=date.year, 
                                    Status=False
                                )
                                protocols_linked += 1

                # === Основной цикл по строкам ===
                for row_idx in range(1, sheet.max_row + 1):
                    cell_a = sheet.cell(row=row_idx, column=1)
                    cell_b = sheet.cell(row=row_idx, column=2)
                    cell_c = sheet.cell(row=row_idx, column=3)
                    cell_d = sheet.cell(row=row_idx, column=4)
                    
                    val_a = cell_a.value
                    val_b = cell_b.value
                    val_c = cell_c.value
                    val_d = cell_d.value

                    str_a = str(val_a).strip() if val_a is not None else ""
                    str_b = str(val_b).strip() if val_b is not None else ""
                    str_c = str(val_c).strip() if val_c is not None else ""
                    str_d = str(val_d).strip() if val_d is not None else ""

                    # 1. ПОИСК ДАТЫ
                    found_date = None
                    if isinstance(val_a, datetime):
                        found_date = val_a
                    elif str_a:
                        date_match = re.search(r'(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})', str_a)
                        if date_match:
                            date_str = date_match.group(1)
                            for fmt in ['%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%y']:
                                try:
                                    found_date = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                    
                    if found_date:
                        # Перед сменой даты сохраняем предыдущий слот (если он был)
                        if current_slot['time']:
                            save_slot(current_slot, current_date)
                        
                        print(f"📅 [Row {row_idx}] Новая дата: {found_date.date()}")
                        current_date = found_date
                        # Сбрасываем слот для новой даты
                        current_slot = {'time': None, 'auditorium': None, 'count': 0, 'students': []}
                        continue

                    # 2. ПОИСК ВРЕМЕНИ (Начало нового слота)
                    time_match = re.match(r'^(\d{2}:\d{2})-(\d{2}:\d{2})$', str_a)
                    
                    if time_match:
                        # Если уже был активный слот, сохраняем его перед началом нового
                        if current_slot['time']:
                            save_slot(current_slot, current_date)
                        
                        current_slot['time'] = str_a
                        current_slot['auditorium'] = str_b if str_b else "Не указана"
                        current_slot['students'] = [] # Очищаем список студентов
                        
                        # 🔥 ВАЖНО: Определяем Count через объединенные ячейки в столбце B (Аудитория)
                        merged_count = 0
                        for merged_range in sheet.merged_cells.ranges:
                            # Ищем объединение, которое начинается в текущей строке и находится во 2-м столбце
                            if merged_range.min_row == row_idx and merged_range.min_col == 2 and merged_range.max_col == 2:
                                merged_count = merged_range.max_row - merged_range.min_row + 1
                                break
                        
                        # Если объединения нет, считаем как 1 строка
                        current_slot['count'] = merged_count if merged_count > 0 else 1
                        
                        print(f"⏰ [Row {row_idx}] Новый слот: {current_slot['time']}, Ауд: {current_slot['auditorium']}, Выделено мест (Count): {current_slot['count']}")
                        
                        # Если в строке со временем сразу есть студент (редко, но бывает)
                        if str_c and str_d and str_d.lower() != 'тема проекта':
                            current_slot['students'].append((str_c, str_d))
                            
                        continue

                    # 3. ОБРАБОТКА СТРОК С ДАННЫМИ (Студенты внутри текущего слота)
                    if current_date and current_slot['time']:
                        # Если есть Группа и Тема, добавляем в текущий слот
                        if str_c and str_d and str_d.lower() != 'тема проекта':
                            current_slot['students'].append((str_c, str_d))
                            # print(f"   ➕ Студент: {str_c} | {str_d[:30]}")

                # После окончания цикла сохраняем последний слот на листе
                if current_slot['time']:
                    print(f"🔄 Конец листа. Сохраняю последний слот...")
                    save_slot(current_slot, current_date)

        print(f"\n=== 🏁 ИТОГ ===")
        print(f"✅ defenses_added: {defenses_added}, protocols_linked: {protocols_linked}")
        
        return {
            "status": "success",
            "defenses_added": defenses_added,
            "protocols_linked": protocols_linked
        }

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}