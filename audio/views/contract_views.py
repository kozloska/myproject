import os
import io
import re
import zipfile
import shutil
import tempfile
from datetime import datetime

from django.http import JsonResponse, HttpResponse
from django.views import View
from openpyxl import load_workbook
from docx import Document

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

_ONES_MALE = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
_ONES_FEMALE = ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
_TEENS = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
          'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']
_TENS = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят',
         'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
_HUNDREDS = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот',
             'шестьсот', 'семьсот', 'восемьсот', 'девятьсот']

_GROUPS = [
    (10 ** 9, ('миллиард', 'миллиарда', 'миллиардов'), False),
    (10 ** 6, ('миллион', 'миллиона', 'миллионов'), False),
    (10 ** 3, ('тысяча', 'тысячи', 'тысяч'), True),
]


def _plural(n, forms):
    n = abs(int(n)) % 100
    if 11 <= n <= 14:
        return forms[2]
    n2 = n % 10
    if n2 == 1:
        return forms[0]
    if 2 <= n2 <= 4:
        return forms[1]
    return forms[2]


def _three_digits_to_words(n, feminine=False):
    words = []
    h, r = divmod(n, 100)
    if h:
        words.append(_HUNDREDS[h])
    if 10 <= r < 20:
        words.append(_TEENS[r - 10])
    else:
        t, o = divmod(r, 10)
        if t:
            words.append(_TENS[t])
        if o:
            words.append((_ONES_FEMALE if feminine else _ONES_MALE)[o])
    return words


def num_to_words_ru(n):
    n = int(n)
    if n == 0:
        return 'ноль'
    words = []
    remaining = n
    for div, forms, feminine in _GROUPS:
        if remaining >= div:
            count = remaining // div
            remaining %= div
            words.extend(_three_digits_to_words(count, feminine=feminine))
            words.append(_plural(count, forms))
    if remaining:
        words.extend(_three_digits_to_words(remaining, feminine=False))
    return ' '.join(words)


def sum_to_full_str(amount):
    amount = float(amount)
    rub = int(amount)
    kop = int(round((amount - rub) * 100))

    if amount == rub:
        amount_display = str(rub)
    else:
        amount_display = f"{amount:.2f}".rstrip('0').rstrip('.')

    words = num_to_words_ru(rub)  # уже в нижнем регистре
    rub_word = _plural(rub, ('рубль', 'рубля', 'рублей'))
    kop_word = _plural(kop, ('копейка', 'копейки', 'копеек'))

    return f"{amount_display} ({words} {rub_word} {kop:02d} {kop_word})"

def _clean(value):
    """Убирает лишний .0 у чисел, приводит к строке, режет пробелы."""
    if value is None:
        return ''
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return str(value)
    return str(value).strip()


def _format_passport_series(value):
    """2515 -> '25 15' (стандартный вид серии паспорта РФ)."""
    s = _clean(value)
    if len(s) == 4 and s.isdigit():
        return f"{s[:2]} {s[2:]}"
    return s


def make_initials(fio):
    """
    'Козлова Вероника Александровна' -> 'В.А. Козлова'
    ФИО в Excel хранится как 'Фамилия Имя Отчество'.
    """
    parts = [p for p in fio.split() if p]
    if not parts:
        return ''
    surname = parts[0]
    initials = ''.join(f"{p[0].upper()}." for p in parts[1:3])
    return f"{initials} {surname}".strip() if initials else surname


def _replace_placeholders_in_paragraph(paragraph, replacements):
    runs = paragraph.runs
    if not runs:
        return

    orig_texts = [r.text for r in runs]
    full_text = ''.join(orig_texts)
    if not full_text or not any(key in full_text for key in replacements):
        return

    pattern = re.compile('|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True)))
    matches = list(pattern.finditer(full_text))
    if not matches:
        return

    spans = []
    pos = 0
    for t in orig_texts:
        spans.append((pos, pos + len(t)))
        pos += len(t)

    new_texts = list(orig_texts)

    # Совпадения, целиком лежащие в одном run, можно безопасно заменить
    # локальным re.sub по этому run (учитывает несколько плейсхолдеров в одном run).
    single_run_idx = set()
    cross_run_matches = []
    for m in matches:
        start, end = m.start(), m.end()
        covered = [i for i, (s, e) in enumerate(spans) if s < end and e > start]
        if len(covered) == 1:
            single_run_idx.add(covered[0])
        else:
            cross_run_matches.append((m, covered))

    for i in single_run_idx:
        new_texts[i] = pattern.sub(lambda mm: replacements[mm.group(0)], orig_texts[i])

    for m, covered in cross_run_matches:
        start, end = m.start(), m.end()
        value = replacements[m.group(0)]
        first_idx, last_idx = covered[0], covered[-1]
        first_s = spans[first_idx][0]
        last_s = spans[last_idx][0]
        prefix = orig_texts[first_idx][: start - first_s]
        suffix = orig_texts[last_idx][end - last_s:]
        new_texts[first_idx] = prefix + value
        new_texts[last_idx] = suffix
        for i in range(first_idx + 1, last_idx):
            new_texts[i] = ''

    for i, run in enumerate(runs):
        if new_texts[i] != orig_texts[i]:
            run.text = new_texts[i]

@method_decorator(csrf_exempt, name='dispatch')
class ContractGenerate(View):


    SHEET_NAME = 'Лист1'
    FIO_COL = 0
    SUM_COL = 1
    DISCOUNT_COL = 2
    PASSPORT_SERIES_COL = 3
    PASSPORT_NUMBER_COL = 4
    ISSUED_COL = 5
    CODE_COL = 6
    SNILS_COL = 7
    INN_COL = 8
    TELEPHONE_COL = 9
    EMAIL_COL = 10

    def post(self, request):
        try:
            excel_file = request.FILES.get('excel_file')
            template_file = request.FILES.get('template_file')

            if not excel_file or not template_file:
                return JsonResponse({'error': 'Необходимо загрузить Excel и шаблон Word'}, status=400)

            try:
                start_number = int(request.POST.get('start_number', 1))
            except (TypeError, ValueError):
                start_number = 1

            current_year = datetime.now().year

            temp_dir = tempfile.mkdtemp()
            try:
                excel_path = os.path.join(temp_dir, 'input.xlsx')
                template_path = os.path.join(temp_dir, 'template.docx')
                output_dir = os.path.join(temp_dir, 'output')
                os.makedirs(output_dir)

                with open(excel_path, 'wb+') as f:
                    for chunk in excel_file.chunks():
                        f.write(chunk)

                with open(template_path, 'wb+') as f:
                    for chunk in template_file.chunks():
                        f.write(chunk)

                wb = load_workbook(excel_path, data_only=True)
                if self.SHEET_NAME not in wb.sheetnames:
                    return JsonResponse({
                        'error': f"Лист '{self.SHEET_NAME}' не найден. Доступные: {wb.sheetnames}"
                    }, status=400)

                ws = wb[self.SHEET_NAME]
                # данные начинаются с 3-й строки (1-я и 2-я - заголовки)
                rows = list(ws.iter_rows(min_row=3, values_only=True))

                generated_files = []
                count = 0
                contract_number = start_number

                for row in rows:
                    max_col_index = max(
                        self.FIO_COL, self.SUM_COL, self.PASSPORT_SERIES_COL,
                        self.PASSPORT_NUMBER_COL, self.ISSUED_COL, self.CODE_COL,
                        self.SNILS_COL, self.INN_COL, self.TELEPHONE_COL, self.EMAIL_COL,
                    )
                    if len(row) <= max_col_index:
                        continue

                    fio = _clean(row[self.FIO_COL])
                    if not fio:
                        continue

                    sum_raw = row[self.SUM_COL]
                    if sum_raw is None:
                        continue

                    fio_str = fio
                    sum_str = sum_to_full_str(sum_raw)

                    discount_raw = row[self.DISCOUNT_COL]
                    if discount_raw not in (None, '', 0):
                        discount_str = _clean(discount_raw)
                        sum_str += f", предоставляется  {discount_str}% скидка"

                    passport_str = (
                        f"Серия: {_format_passport_series(row[self.PASSPORT_SERIES_COL])} "
                        f"Номер: {_clean(row[self.PASSPORT_NUMBER_COL])}"
                    )

                    replacements = {
                        '{number}': str(contract_number),
                        '{year}': str(current_year),
                        '{fio}': fio_str,
                        '{initials}': make_initials(fio_str),
                        '{sum}': sum_str,
                        '{Passport}': passport_str,
                        '{lssued}': _clean(row[self.ISSUED_COL]),
                        '{code}': _clean(row[self.CODE_COL]),
                        '{SNILS}': _clean(row[self.SNILS_COL]),
                        '{INN}': _clean(row[self.INN_COL]),
                        '{Telephone}': _clean(row[self.TELEPHONE_COL]),
                        '{Email}': _clean(row[self.EMAIL_COL]),
                    }

                    safe_name = fio_str.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    filename = f"Договор_{contract_number}_{safe_name}.docx"
                    file_path = os.path.join(output_dir, filename)

                    shutil.copy2(template_path, file_path)
                    self._replace_in_docx(file_path, replacements)
                    generated_files.append(file_path)

                    count += 1
                    contract_number += 1

                if count == 0:
                    return JsonResponse({
                        'error': 'Не найдено данных для генерации. Проверьте, что в листе есть ФИО и стоимость.'
                    }, status=400)

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in generated_files:
                        arcname = os.path.basename(file_path)
                        zip_file.write(file_path, arcname)

                zip_buffer.seek(0)

                response = HttpResponse(
                    zip_buffer.getvalue(),
                    content_type='application/zip'
                )
                response['Content-Disposition'] = 'attachment; filename="contracts.zip"'

                return response

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Ошибка сервера: {str(e)}'}, status=500)

    def _replace_in_docx(self, doc_path, replacements):
        doc = Document(doc_path)

        for paragraph in doc.paragraphs:
            _replace_placeholders_in_paragraph(paragraph, replacements)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        _replace_placeholders_in_paragraph(paragraph, replacements)

        doc.save(doc_path)