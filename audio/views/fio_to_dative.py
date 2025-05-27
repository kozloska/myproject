from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from natasha import Doc, Segmenter
from pymorphy2 import MorphAnalyzer
from ..serializers import FIOSerializer

class FIOToDativeView(APIView):
    def post(self, request, *args, **kwargs):
        # Сериализация и валидация входных данных
        serializer = FIOSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        fio = serializer.validated_data['fio'].strip()

        # Инициализация
        segmenter = Segmenter()
        morph_analyzer = MorphAnalyzer()
        doc = Doc(fio)
        doc.segment(segmenter)

        # Определяем пол на основе имени и отчества
        tokens = [token.text for token in doc.tokens]
        is_female = False
        if len(tokens) > 1:
            name = tokens[1]
            parsed_name = morph_analyzer.parse(name)
            if parsed_name and 'femn' in parsed_name[0].tag:
                is_female = True
        # Проверяем отчество на типичные мужские окончания
        if len(tokens) > 2 and tokens[2].endswith('ич'):
            is_female = False
        # Проверяем отчество на типичные женские окончания
        if len(tokens) > 2 and tokens[2].endswith('вна'):
            is_female = True
        # Если фамилия заканчивается на -ова или -ёва, считаем её женской
        if len(tokens) > 0 and (tokens[0].endswith('ова') or tokens[0].endswith('ёва') or tokens[0].endswith('ая')):
            is_female = True

        # Преобразуем каждое слово в дательный падеж
        dative_fio = []
        for i, token in enumerate(doc.tokens):
            text = token.text.lower()  # Приводим к нижнему регистру для единообразия
            parsed = morph_analyzer.parse(text)

            if parsed:
                # Учитываем пол для фамилии (первое слово)
                if i == 0:  # Обрабатываем фамилию
                    # Женские фамилии на -ова, -ёва, -ая
                    if is_female and (text.endswith('ова') or text.endswith('ёва')):
                        if text.endswith('ёва'):
                            dative_form = text[:-3] + 'ёвой'  # "михалёва" -> "михалёвой"
                        else:
                            dative_form = text[:-3] + 'овой'  # "козлова" -> "козловой"
                    elif is_female and text.endswith('ая'):
                        dative_form = text[:-2] + 'ой'  # "жужговская" -> "жужговской"
                    # Мужские фамилии на согласные
                    elif not is_female and text[-1] in 'бвгджзйклмнпрстфхцчшщ':
                        dative_form = text + 'у'  # "шмуцлер" -> "шмуцлеру"
                    # Составные фамилии (например, "Чугунова-Крылья")
                    elif '-' in text:
                        parts = text.split('-')
                        dative_parts = []
                        for part in parts:
                            parsed_part = morph_analyzer.parse(part)
                            if parsed_part:
                                if is_female and (part.endswith('ова') or part.endswith('ёва')):
                                    if part.endswith('ёва'):
                                        dative_part = part[:-3] + 'ёвой'
                                    else:
                                        dative_part = part[:-3] + 'овой'
                                elif is_female and part.endswith('ья'):
                                    dative_part = part[:-2] + 'ьям'
                                elif not is_female and part[-1] in 'бвгджзйклмнпрстфхцчшщ':
                                    dative_part = part + 'у'
                                else:
                                    dative_part = parsed_part[0].inflect({'datv'}).word if parsed_part[0].inflect({'datv'}) else part
                            else:
                                dative_part = part
                        dative_form = '-'.join(dative_parts)
                    # Фамилии с апострофами или пробелами (например, "О'Коннор", "Фон Штейн")
                    elif "'" in text or " " in text:
                        dative_form = text + ' (не склонено)'
                    else:
                        dative_form = parsed[0].inflect({'datv'}).word if parsed[0].inflect({'datv'}) else text
                else:
                    # Склоняем имя и отчество
                    dative_form = parsed[0].inflect({'datv'}).word if parsed[0].inflect({'datv'}) else text
            else:
                # Если не удалось разобрать, применяем простые правила
                if i == 0:
                    if not is_female and text[-1] in 'бвгджзйклмнпрстфхцчшщ' and len(text) > 2:
                        dative_form = text + 'у'
                    elif is_female and text[-1] == 'а':
                        dative_form = text[:-1] + 'е'
                    else:
                        dative_form = text + ' (не склонено)'
                else:
                    dative_form = text + ' (не склонено)'

            dative_fio.append(dative_form)

        result = ' '.join(dative_fio)
        # Добавляем результат в данные для сериализации
        response_data = {'fio': fio, 'dative_fio': result}
        return Response(response_data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response({'error': 'Метод не поддерживается'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)