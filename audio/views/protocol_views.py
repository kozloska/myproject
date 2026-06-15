from django_filters.rest_framework import DjangoFilterBackend
from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from ..filters import ProtocolFilter
from ..models import Protocol, Student
from ..serializers import ProtocolSerializer, UpdateGradeSerializer, ProtocolArchiveLiteSerializer
from rest_framework import viewsets, status
from django.db.models import Q
from openpyxl.styles import Font, PatternFill
from io import BytesIO

class ProtocolViewSet(viewsets.ModelViewSet):
    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter  

    def get_queryset(self):
        queryset = Protocol.objects.select_related(
            'ID_Student',                          # Студент
            'ID_Student__ID_Group',                # Группа студента
            'ID_Student__ID_Specialization',       # Специализация студента
            'ID_Student__ID_Project',              # Проект студента
            'ID_Student__ID_Qualification',        # Квалификация студента
            'ID_DefenseSchedule',                  # Расписание защиты
            'ID_DefenseSchedule__ID_Commission',   # Комиссия
        ).all()
        return queryset.order_by('-Year', 'Number')
    
    def perform_update(self, serializer):
        # 1. Сохраняем изменения в протоколе
        protocol = serializer.save()
        
        # 2. Проверяем, что запрос касался изменения расписания
        if 'ID_DefenseSchedule' in self.request.data:
            # 3. Безопасно добираемся до проекта
            if protocol.ID_Student and protocol.ID_Student.ID_Project:
                project = protocol.ID_Student.ID_Project
                
                # 4. Обновляем статус (только это поле, чтобы не триггерить лишние сигналы)
                project.Status = "Защита не начата"
                project.save(update_fields=['Status'])

class ProtocolArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProtocolArchiveLiteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProtocolFilter

    def get_queryset(self):
        return Protocol.objects.select_related(
            'ID_Student',
            'ID_Student__ID_Group',
            'ID_Student__ID_Specialization',
            'ID_Student__ID_Project',
            'ID_Student__ID_Qualification',
            'ID_DefenseSchedule',
            'ID_DefenseSchedule__ID_Commission',
        ).filter(Status=True).order_by('-Year', 'Number')

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Экспорт протоколов в Excel"""
        # ✅ Используем get_queryset() + prefetch_related для секретаря
        queryset = self.get_queryset().prefetch_related(
            'ID_DefenseSchedule__ID_Commission__commissioncomposition_set',
            'ID_DefenseSchedule__ID_Commission__commissioncomposition_set__ID_Member',
        )

        # Применяем фильтры из запроса
        filterset = self.filterset_class(
            request.query_params,
            queryset=queryset,
            request=request
        )
        if filterset.is_valid():
            queryset = filterset.qs

        # ✅ Поиск по ФИО с использованием Q объектов
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(ID_Student__Surname__icontains=search_query) |
                Q(ID_Student__Name__icontains=search_query) |
                Q(ID_Student__Patronymic__icontains=search_query)
            )

        # Создаем Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Протоколы"

        # Заголовки
        headers = [
            'Направление', 'Секретарь', 'Группа', 'ФИО студента',
            '№ протокола', 'Дата защиты', 'Квалификация', 'Тема проекта', 'Оценка'
        ]
        ws.append(headers)

        # Стилизация заголовков
        header_fill = PatternFill(start_color="4892B4", end_color="4892B4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Добавляем данные
        for protocol in queryset:
            student = protocol.ID_Student

            # ✅ Получаем секретаря из комиссии (без доп. запросов благодаря prefetch_related)
            secretary_name = '—'
            if protocol.ID_DefenseSchedule and protocol.ID_DefenseSchedule.ID_Commission:
                commission = protocol.ID_DefenseSchedule.ID_Commission
                for member in commission.commissioncomposition_set.all():
                    if member.Role == 'Секретарь' and member.ID_Member:
                        secretary_name = f"{member.ID_Member.Surname or ''} {member.ID_Member.Name or ''} {member.ID_Member.Patronymic or ''}".strip()
                        break

            # Формируем строку данных
            row = [
                student.ID_Specialization.Name if student and student.ID_Specialization else '—',
                secretary_name,
                student.ID_Group.Name if student and student.ID_Group else '—',
                f"{student.Surname or ''} {student.Name or ''} {student.Patronymic or ''}".strip() if student else 'Студент удален',
                protocol.Number or protocol.ID,
                protocol.ID_DefenseSchedule.DateTime.strftime('%d.%m.%Y') if protocol.ID_DefenseSchedule and protocol.ID_DefenseSchedule.DateTime else '—',
                student.ID_Qualification.Name if student and student.ID_Qualification else 'Бакалавр',
                student.ID_Project.Title if student and student.ID_Project else '—',
                protocol.Grade or '—',
            ]
            ws.append(row)

        # Автоматическая ширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Сохраняем в память
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Возвращаем файл
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="Протоколы.xlsx"'

        return response