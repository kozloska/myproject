from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from natasha import MorphVocab, Doc, Segmenter
from pymorphy3 import MorphAnalyzer
import json


@csrf_exempt
def fio_to_dative(request):
    if request.method == 'POST':
        try:
            # Получаем данные из multipart/form-data через request.POST
            fio = request.POST.get('fio', '').strip()

            if not fio:
                return JsonResponse({'error': 'ФИО не указано'}, status=400)

            # Инициализация Natasha и pymorphy3
            segmenter = Segmenter()
            morph_analyzer = MorphAnalyzer()
            doc = Doc(fio)
            doc.segment(segmenter)

            # Преобразуем каждое слово в дательный падеж
            dative_fio = []
            for token in doc.tokens:
                parsed = morph_analyzer.parse(token.text)
                if parsed:
                    dative_form = parsed[0].inflect({'datv'}).word if parsed[0].inflect({'datv'}) else token.text
                    dative_fio.append(dative_form)
                else:
                    dative_fio.append(token.text)

            result = ' '.join(dative_fio)
            return JsonResponse({'dative_fio': result}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)