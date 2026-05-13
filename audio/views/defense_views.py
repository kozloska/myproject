from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime
from django.db.models import Exists, OuterRef, Q

from ..models import DefenseSchedule, Project, Protocol
from ..serializers import DefenseScheduleSerializer
from ..filters import DefenseScheduleFilter

class DefenseViewSet(viewsets.ModelViewSet):
    queryset = DefenseSchedule.objects.all()
    serializer_class = DefenseScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DefenseScheduleFilter

    def get_queryset(self):
        # Текущая дата и время с учётом часового поюза
        now = timezone.now()
        # Начало года
        start_of_year = datetime(now.year, 1, 1, 0, 0, 0)
        start_of_year = timezone.make_aware(start_of_year)
        
        # Конец текущего года (31 декабря 23:59:59)
        end_of_year = datetime(now.year, 12, 31, 23, 59, 59)
        end_of_year = timezone.make_aware(end_of_year)

        # Фильтруем записи по диапазону дат
        queryset = DefenseSchedule.objects.filter(
            DateTime__gte=start_of_year,
            DateTime__lte=end_of_year
        )

        # Применяем дополнительные фильтры
        return self.filterset_class(self.request.GET, queryset=queryset, request=self.request).qs
    
    @action(detail=False, methods=['get'], url_path='with-pending-projects')
    def with_pending_projects(self, request):
        now = timezone.now()
        start_of_year = timezone.make_aware(datetime(now.year, 1, 1, 0, 0, 0))
        end_of_year = timezone.make_aware(datetime(now.year, 12, 31, 23, 59, 59))

        # Базовый фильтр по году
        queryset = DefenseSchedule.objects.filter(
            DateTime__gte=start_of_year,
            DateTime__lte=end_of_year
        )

        # Исправленная логика Exists:
        # Мы ищем Протоколы, которые привязаны к текущему DefenseSchedule (через OuterRef('pk'))
        # И у которых есть студент с проектом (ID_Student__ID_Project__isnull=False)
        # И статус протокола False (не утвержден)
        # И оценка существует
        has_pending_work = Exists(
            Protocol.objects.filter(
                ID_DefenseSchedule=OuterRef('pk'),  # Связь Protocol -> DefenseSchedule
                ID_Student__ID_Project__isnull=False, # У студента должен быть проект
                Status=False,                       # Протокол ещё не утверждён
                Grade__isnull=False,                # Оценка уже выставлена
                # Grade__gt='' можно добавить, если нужно исключить пустые строки, 
                # но CharField с оценками лучше проверять на isnull
            )
        )
        
        queryset = queryset.filter(has_pending_work)

        # Применяем внешние фильтры (например, по специализации из GET-параметров)
        # Важно: filterset_class должен корректно обрабатывать уже отфильтрованный queryset
        filtered_queryset = self.filterset_class(request.GET, queryset=queryset, request=request).qs

        # Пагинация
        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)