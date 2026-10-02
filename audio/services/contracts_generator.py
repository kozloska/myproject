import io
import re
import zipfile
from copy import deepcopy
from datetime import datetime, date
from decimal import Decimal

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table, _Row
from openpyxl import load_workbook

# ---------------------------------------------------------------------------
# Число → пропись (рубли / копейки)
# ---------------------------------------------------------------------------

_ONES = (
    "", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять",
    "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
    "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать",
)
_TENS = (
    "", "", "двадцать", "тридцать", "сорок", "пятьдесят",
    "шестьдесят", "семьдесят", "восемьдесят", "девяносто",
)
_HUNDREDS = (
    "", "сто", "двести", "триста", "четыреста", "пятьсот",
    "шестьсот", "семьсот", "восемьсот", "девятьсот",
)
_THOUSANDS = (
    ("тысяча", "тысячи", "тысяч"),
    ("миллион", "миллиона", "миллионов"),
)

def _morph(n: int, forms: tuple) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]

def _triplet(n: int, feminine: bool = False) -> str:
    """0..999 → слова. feminine=True для тысяч (одна/две)."""
    if n == 0:
        return ""
    parts = []
    parts.append(_HUNDREDS[n // 100])
    n %= 100
    if n < 20:
        word = _ONES[n]
        if feminine and n == 1:
            word = "одна"
        elif feminine and n == 2:
            word = "две"
        parts.append(word)
    else:
        parts.append(_TENS[n // 10])
        ones = n % 10
        word = _ONES[ones]
        if feminine and ones == 1:
            word = "одна"
        elif feminine and ones == 2:
            word = "две"
        parts.append(word)
    return " ".join(p for p in parts if p)

def number_to_words_rub(amount) -> str:
    """
    48760 → 'сорок восемь тысяч семьсот шестьдесят рублей 00 коп'
    """
    if isinstance(amount, str):
        amount = amount.replace(" ", "").replace(",", ".")
    d = Decimal(str(amount)).quantize(Decimal("0.01"))
    rub = int(d)
    kop = int((d - rub) * 100)

    if rub == 0:
        result = "ноль рублей"
    else:
        parts = []
        # миллионы
        millions = rub // 1_000_000
        if millions:
            parts.append(_triplet(millions))
            parts.append(_morph(millions, _THOUSANDS[1]))
        # тысячи
        thousands = (rub // 1000) % 1000
        if thousands:
            parts.append(_triplet(thousands, feminine=True))
            parts.append(_morph(thousands, _THOUSANDS[0]))
        # единицы
        units = rub % 1000
        if units or not parts:
            parts.append(_triplet(units))

        # склонение "рубль"
        last2 = rub % 100
        last1 = rub % 10
        if 11 <= last2 <= 19:
            rub_word = "рублей"
        elif last1 == 1:
            rub_word = "рубль"
        elif 2 <= last1 <= 4:
            rub_word = "рубля"
        else:
            rub_word = "рублей"

        result = " ".join(p for p in parts if p) + " " + rub_word

    return f"{result} {kop:02d} коп"

# ---------------------------------------------------------------------------
# ФИО → инициалы «И.О. Фамилия»
# ---------------------------------------------------------------------------

def make_initials(fio: str) -> str:
    """Иванова Евгения Валерьевна → Е.В. Иванова"""
    parts = [p.strip() for p in str(fio).split() if p.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    surname = parts[0]
    initials = ".".join(p[0].upper() for p in parts[1:]) + "."
    return f"{initials} {surname}"

# ---------------------------------------------------------------------------
# Форматирование дат и номера
# ---------------------------------------------------------------------------

def fmt_date(val) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%d.%m.%Y")
    if isinstance(val, date):
        return val.strftime("%d.%m.%Y")
    s = str(val).strip()
    # уже готовая строка
    return s

def fmt_number(n) -> str:
    """Однозначный → с ведущим нулём (7 → 07)"""
    try:
        n = int(n)
        return f"{n:02d}" if n < 10 else str(n)
    except (TypeError, ValueError):
        return str(n).strip()

# ---------------------------------------------------------------------------
# Работа с python-docx: замена текста (включая разбитые runs)
# ---------------------------------------------------------------------------

def _replace_in_paragraph(paragraph, mapping: dict):
    """Заменяет все вхождения ключей mapping в параграфе, сохраняя форматирование первого run."""
    if not paragraph.runs:
        return
    full = "".join(run.text for run in paragraph.runs)
    new_text = full
    for key, val in mapping.items():
        if key in new_text:
            new_text = new_text.replace(key, str(val) if val is not None else "")
    if new_text == full:
        return
    # пишем всё в первый run, остальные очищаем
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""

def replace_placeholders(doc: Document, mapping: dict):
    """Глобальная замена по всему документу (параграфы + ячейки таблиц)."""
    for p in doc.paragraphs:
        _replace_in_paragraph(p, mapping)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, mapping)

# ---------------------------------------------------------------------------
# Дублирование строк таблицы (для нескольких групп)
# ---------------------------------------------------------------------------

def _clone_row(table: Table, row_idx: int) -> _Row:
    """Клонирует строку таблицы и вставляет сразу после неё."""
    tr = table.rows[row_idx]._tr
    new_tr = deepcopy(tr)
    tr.addnext(new_tr)
    return table.rows[row_idx + 1]

def expand_stages_for_groups(table: Table, groups: list[str], stage_templates: list[dict]):
    """
    table          – таблица с заголовком + 3 строки-шаблона (этапы 1..3)
    groups         – ['МЦб-25-1', 'МЦб-25-2', ...]
    stage_templates – список из 3 dict'ов с ключами:
        'num'   – 'I.' / '2.' / '3.'  (будет перенумерован)
        'text'  – текст с {group}
        'cost'  – стоимость (только для таблицы календаря)
        'dates' – срок приёмки (только для таблицы календаря)
    """
    # удаляем старые data-rows (оставляем только header)
    while len(table.rows) > 1:
        tr = table.rows[1]._tr
        tr.getparent().remove(tr)

    stage_num = 1
    for g in groups:
        for tpl in stage_templates:
            row = table.add_row()
            # номер этапа
            if stage_num == 1:
                num_str = "I."
            else:
                num_str = f"{stage_num}."
            row.cells[0].text = num_str

            text = tpl["text"].replace("{group}", g)
            row.cells[1].text = text

            if len(row.cells) >= 3 and "cost" in tpl:
                row.cells[2].text = tpl["cost"]
            if len(row.cells) >= 4 and "dates" in tpl:
                row.cells[3].text = tpl["dates"]

            stage_num += 1

# ---------------------------------------------------------------------------
# Основная функция генерации одного договора
# ---------------------------------------------------------------------------

def generate_one_contract(template_bytes: bytes, row_data: dict, contract_number: str) -> bytes:
    """
    row_data – словарь с ключами из Excel (нижний регистр / как в заголовках).
    Возвращает bytes готового .docx.
    """
    doc = Document(io.BytesIO(template_bytes))

    fio = str(row_data.get("фио") or "").strip()
    groups_raw = str(row_data.get("группа") or "").strip()
    groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
    if not groups:
        groups = [""]

    sum_val = row_data.get("сумма договора") or 0
    try:
        sum_num = Decimal(str(sum_val).replace(" ", "").replace(",", "."))
    except Exception:
        sum_num = Decimal("0")

    sum_words = number_to_words_rub(sum_num)
    # в шаблоне встречается и "sum.", и "{sum}" и просто "sum"
    sum_full = f"{sum_num:,.0f}".replace(",", " ") + f" ({sum_words})"

    mapping = {
        "{fio}": fio,
        "fio": fio,                          # в акте без скобок
        "{birthday}": fmt_date(row_data.get("дата рождения")),
        "{passport}": str(row_data.get("номер и серия паспорта") or "").strip(),
        "{lssued}": str(row_data.get("кем выдан паспорт") or "").strip(),
        "{datepassport}": fmt_date(row_data.get("дата выдачи паспорта")),
        "{SNILS}": str(row_data.get("СНИЛС") or "").strip(),
        "{INN}": str(row_data.get("ИНН") or "").strip(),
        "{address}": str(row_data.get("адрес регистрации") or "").strip(),
        "{work}": str(row_data.get("место работы") or "").strip(),
        "{group}": ", ".join(groups),
        "{number}": contract_number,
        "number": contract_number,
        "{initials}": make_initials(fio),
        "{ initials }": make_initials(fio),
        "{bank}": str(row_data.get("банк") or "").strip(),
        "{BIK}": str(row_data.get("бик") or "").strip(),
        "{KPP}": str(row_data.get("кпп") or "").strip(),
        "{KS}": str(row_data.get("к/с") or "").strip(),
        "{RS}": str(row_data.get("р/с") or "").strip(),
        "{telephone}": str(row_data.get("номер телефона") or "").strip(),
        # sum – несколько вариантов написания в шаблоне
        "sum.": sum_full + ".",
        "sum": sum_full,
        "{sum}": sum_full,
    }

    # ------------------------------------------------------------------
    # Расширение таблиц при >1 группе
    # ------------------------------------------------------------------
    # TABLE 2 – Календарный план (индекс 2)
    # TABLE 4 – Содержание работ (индекс 4)
    calendar_templates = [
        {
            "text": 'Проведение занятий по дисциплине «1. Основы теории алгоритмов и разработка программного обеспечения», гр. {group}, 32 часа (15.12.2026г.)',
            "cost": "28 800",
            "dates": "30.09.2026г. –\n25.12.2026г.",
        },
        {
            "text": "Организационное и методическое сопровождение обучающихся гр. {group}, 40 часов (15.12.2026г.)",
            "cost": "19 960",
            "dates": "30.09.2026г. –\n25.12.2026г.",
        },
    ]
    content_templates = [
         {
            "text": 'Проведение еженедельных занятий в соответствии с расписанием и прием зачета по дисциплине «1. Основы теории алгоритмов и разработка программного обеспечения», гр. {group}',
        },

        {
            "text": "Проведение индивидуальных консультаций, гр. {group}",
        },
    ]

    if len(groups) > 1:
        # Календарный план
        if len(doc.tables) > 2:
            expand_stages_for_groups(doc.tables[2], groups, calendar_templates)
        # Содержание работ
        if len(doc.tables) > 4:
            expand_stages_for_groups(doc.tables[4], groups, content_templates)
    else:
        # одна группа – просто заменяем {group}
        pass

    # финальная замена всех плейсхолдеров
    replace_placeholders(doc, mapping)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()

# ---------------------------------------------------------------------------
# Генерация ZIP из Excel + шаблона
# ---------------------------------------------------------------------------

def generate_contracts_zip(
    excel_file,
    template_file,
    start_number: int = 1,
) -> bytes:
    """
    excel_file / template_file – file-like или Django UploadedFile.
    Возвращает bytes ZIP-архива.
    """
    # читаем Excel
    wb = load_workbook(excel_file, data_only=True)
    ws = wb.active

    # заголовки (первая строка)
    headers = []
    for cell in ws[1]:
        headers.append(str(cell.value).strip().lower() if cell.value else "")

    # нормализация имён колонок
    col_map = {h: i for i, h in enumerate(headers)}

    # читаем шаблон один раз
    template_bytes = template_file.read()
    if hasattr(template_file, "seek"):
        template_file.seek(0)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        current_num = int(start_number)
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[0]:  # пустая ФИО
                continue

            data = {}
            for h, idx in col_map.items():
                if idx < len(row):
                    data[h] = row[idx]

            # приоритет: колонка «цифра договора», иначе сквозная нумерация
            num_from_excel = data.get("цифра договора")
            if num_from_excel not in (None, ""):
                number = fmt_number(num_from_excel)
            else:
                number = fmt_number(current_num)
                current_num += 1

            docx_bytes = generate_one_contract(template_bytes, data, number)

            # имя файла
            fio_safe = re.sub(r'[\\/*?:"<>|]', "_", str(data.get("фио") or "contract"))
            filename = f"Договор_ЦК-ПИИИ-{number}_26_{fio_safe}.docx"
            zf.writestr(filename, docx_bytes)

    zip_buffer.seek(0)
    return zip_buffer.read()