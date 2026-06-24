import os
import io
import zipfile
import shutil
import tempfile
from django.http import JsonResponse, HttpResponse
from django.views import View
from openpyxl import load_workbook
from docx import Document

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class CertificateGenerate(View):
    def post(self, request):
        try:
            # 1. Получаем файлы и параметры
            excel_file = request.FILES.get('excel_file')
            template_file = request.FILES.get('template_file')
            
            if not excel_file or not template_file:
                return JsonResponse({'error': 'Необходимо загрузить Excel и шаблон Word'}, status=400)
            
            sheet_name = 'Лист1'
            number_col = 0
            fio_col = 1
          
            # 2. Создаем временную директорию
            temp_dir = tempfile.mkdtemp()
            try:
                excel_path = os.path.join(temp_dir, 'input.xlsx')
                template_path = os.path.join(temp_dir, 'template.docx')
                output_dir = os.path.join(temp_dir, 'output')
                os.makedirs(output_dir)

                # Сохраняем загруженные файлы
                with open(excel_path, 'wb+') as f:
                    for chunk in excel_file.chunks():
                        f.write(chunk)
                
                with open(template_path, 'wb+') as f:
                    for chunk in template_file.chunks():
                        f.write(chunk)

                # 3. Читаем Excel
                wb = load_workbook(excel_path)
                if sheet_name not in wb.sheetnames:
                    return JsonResponse({
                        'error': f"Лист '{sheet_name}' не найден. Доступные: {wb.sheetnames}"
                    }, status=400)
                
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(min_row=2, values_only=True))
                
                generated_files = []
                count = 0

                for row in rows:
                    # Проверка границ столбцов
                    max_col_index = max(number_col, fio_col)
                    if len(row) <= max_col_index:
                        continue
                    
                    reg_number = row[number_col]
                    full_name = row[fio_col]

                    # Форматирование данных
                    if isinstance(reg_number, float):
                        reg_number_str = str(int(reg_number))
                    else:
                        reg_number_str = str(reg_number).strip()
                    
                    full_name_str = str(full_name).strip()
                    
                    # Словарь замен: покрываем оба формата шаблонов (со скобками и без)
                    replacements = {
                        'number': reg_number_str,
                        'fio': full_name_str,
                        '{number}': reg_number_str,
                        '{ fio }': full_name_str,
                        '{fio}': full_name_str,
                        '{ fio}': full_name_str,
                        '{fio }': full_name_str,
                    }

                    # Генерация имени файла
                    safe_name = full_name_str.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    filename = f"Удостоверение_{reg_number_str}_{safe_name}.docx"
                    file_path = os.path.join(output_dir, filename)

                    # Копируем шаблон и заполняем
                    shutil.copy2(template_path, file_path)
                    
                    # Вызываем функцию замены
                    self._replace_in_docx(file_path, replacements)
                    generated_files.append(file_path)
                    count += 1

                if count == 0:
                    return JsonResponse({'error': 'Не найдено данных для генерации. Проверьте, что в выбранном листе есть номера и ФИО.'}, status=400)

                # 4. Упаковываем в ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in generated_files:
                        arcname = os.path.basename(file_path)
                        zip_file.write(file_path, arcname)

                zip_buffer.seek(0)

                # 5. Возвращаем файл
                response = HttpResponse(
                    zip_buffer.getvalue(),
                    content_type='application/zip'
                )
                response['Content-Disposition'] = 'attachment; filename="certificates.zip"'
                
                return response

            finally:
                # Очистка
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Ошибка сервера: {str(e)}'}, status=500)

    def _replace_in_docx(self, doc_path, replacements):
        doc = Document(doc_path)
        
        for paragraph in doc.paragraphs:
            full_text = paragraph.text
            # Проверяем, есть ли что менять
            if any(key in full_text for key in replacements.keys()):
                new_text = full_text
                for old, new in replacements.items():
                    new_text = new_text.replace(old, new)
                
                # Очищаем runs и записываем новый текст
                for run in paragraph.runs:
                    run.text = ""
                if paragraph.runs:
                    paragraph.runs[0].text = new_text
                else:
                    paragraph.add_run(new_text)

        # Обработка таблиц
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        full_text = paragraph.text
                        if any(key in full_text for key in replacements.keys()):
                            new_text = full_text
                            for old, new in replacements.items():
                                new_text = new_text.replace(old, new)
                            
                            for run in paragraph.runs:
                                run.text = ""
                            if paragraph.runs:
                                paragraph.runs[0].text = new_text
                            else:
                                paragraph.add_run(new_text)
                                
        doc.save(doc_path)