# audio/views.py
import requests
from rest_framework.views import APIView
from rest_framework import serializers
from django.http import JsonResponse
from django.conf import settings
from ..models import CommissionMember
import django_filters

class BitrixAuthView(APIView):
    permission_classes = []

    class InnerSerializer(serializers.Serializer):
        code = serializers.CharField()

    def get(self, request, *args, **kwargs):
        serializer = self.InnerSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return self.process_auth(serializer.validated_data)

    def post(self, request, *args, **kwargs):
        serializer = self.InnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.process_auth(serializer.validated_data)

    def process_auth(self, validated_data):
        # Обмен кода на токен
        token_url = "https://int.istu.edu/oauth/token/"
        token_response = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": validated_data['code'],
                "client_id": settings.BITRIX_CLIENT_ID,
                "client_secret": settings.BITRIX_SECRET_KEY,
                "redirect_uri": "http://localhost:9000/api/accounts/bitrix-auth/"
            },
            verify=False
        )

        if token_response.status_code != 200:
            return JsonResponse({"error": token_response.json().get('error_description', 'Ошибка обмена токена')}, status=400)

        token_data = token_response.json()
        access_token = token_data['access_token']
        client_endpoint = token_data['client_endpoint']

        # Получение данных пользователя
        user_info_url = f"{client_endpoint}user.info.json"
        user_info_response = requests.get(
            user_info_url,
            params={"auth": access_token},
            verify=False
        )

        if user_info_response.status_code != 200:
            return JsonResponse({"error": user_info_response.json().get('error_description', 'Ошибка получения данных')}, status=400)

        user_data = user_info_response.json()['result']
        full_name = " ".join(filter(None, [user_data.get('last_name'), user_data.get('name'), user_data.get('second_name')])).strip().lower()

        # Разделяем full_name на Фамилию, Имя и Отчество
        name_parts = full_name.split()
        surname = name_parts[0] if len(name_parts) > 0 else ''
        name = name_parts[1] if len(name_parts) > 1 else ''
        patronymic = name_parts[2] if len(name_parts) > 2 else ''

        try:
            secretary = CommissionMember.objects.filter(
                Surname__iexact=surname,
                Name__iexact=name,
                Patronymic__iexact=patronymic
            ).first()  # Берем только первую запись

            if secretary:
                response_data = [{
                    "ID": secretary.ID,
                    "Surname": secretary.Surname,
                    "Name": secretary.Name,
                    "Patronymic": secretary.Patronymic
                }]
            else:
                response_data = []
                print("Совпадений не найдено")  # Отладка
        except Exception as e:
            return JsonResponse({"error": f"Ошибка поиска: {str(e)}"}, status=400)

        return JsonResponse(response_data, safe=False)