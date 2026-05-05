from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import os
import tempfile
import logging

from django.views.decorators.csrf import csrf_exempt

from audio.models import Specialization
from audio.services.parse_excel_file import parse_excel_file, parse_defense_schedule

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class UploadExcelView(View):
    def post(self, request):
        """
        Обработчик POST-запроса для загрузки и парсинга Excel-файла.
        Ожидает multipart/form-data с полями:
        - Excel-файл (.xlsx)
        - specialization_id (обязательно)
        """
        try:
            # Проверяем наличие файла и specialization_id
            if 'file' not in request.FILES or 'file' not in request.FILES or 'specialization_id' not in request.POST:
                logger.error("Missing file or specialization_id in request")
                return JsonResponse(
                    {"status": "error",
                     "message": "File and specialization_id must be provided"},
                    status=400
                )

            # Получаем файл и параметры
            excel_file = request.FILES['file']
            specialization_id = request.POST['specialization_id']

            # Валидация specialization_id
            try:
                specialization_id = int(specialization_id)
            except ValueError:
                logger.error("Invalid specialization_id format")
                return JsonResponse(
                    {"status": "error",
                     "message": "specialization_id must be an integer"},
                    status=400
                )

            # Сохраняем файл во временную директорию на сервере
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                for chunk in excel_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name

            # Вызываем метод parse_excel_file
            result = parse_excel_file(
                file_path=tmp_file_path,
                specialization_id=specialization_id,
            )

            # Удаляем временный файл
            try:
                os.remove(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_file_path}: {str(e)}")

            # Возвращаем результат
            return JsonResponse(result, status=200 if result['status'] == 'success' else 400)

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return JsonResponse(
                {"status": "error",
                 "message": f"Server error: {str(e)}"},
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class UploadDefenseScheduleView(View):
    def post(self, request):
        """
        Обработчик POST-запроса для загрузки и парсинга Excel-файла с расписанием защит.
        Ожидает multipart/form-data с полями:
        - file: Excel-файл (.xlsx, .xls)
        - specialization_id: ID направления подготовки (обязательно)
        """
        try:
            # ✅ 1. Проверка наличия файла
            if 'file' not in request.FILES:
                logger.error("Missing file in request")
                return JsonResponse(
                    {"status": "error", "message": "File must be provided"},
                    status=400
                )

            # ✅ 2. Проверка наличия и валидности specialization_id
            specialization_id = request.POST.get('specialization_id')
            if not specialization_id:
                return JsonResponse(
                    {"status": "error", "message": "specialization_id is required"},
                    status=400
                )

            try:
                specialization_id = int(specialization_id)
            except (ValueError, TypeError):
                return JsonResponse(
                    {"status": "error", "message": "Invalid specialization_id format"},
                    status=400
                )

            # ✅ 3. Проверка существования специальности в БД
            try:
                specialization = Specialization.objects.get(ID=specialization_id)
            except Specialization.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Specialization not found"},
                    status=404
                )

            excel_file = request.FILES['file']

            # ✅ 4. Сохранение файла во временное хранилище
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                for chunk in excel_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name

            # ✅ 5. Вызов парсера с передаём specialization_id
            result = parse_defense_schedule(
                file_path=tmp_file_path,
                specialization_id=specialization_id  # ✅ Передаём ID
            )

            # ✅ 6. Очистка временного файла
            try:
                os.remove(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_file_path}: {str(e)}")

            # ✅ 7. Возврат результата
            status_code = 200 if result.get('status') == 'success' else 400
            return JsonResponse(result, status=status_code)

        except Exception as e:
            logger.error(f"Error processing defense schedule request: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": f"Server error: {str(e)}"},
                status=500
            )