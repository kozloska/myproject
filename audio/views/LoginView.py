# views.py
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes

# --- Вход ---
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        login_val = request.data.get('login')
        password = request.data.get('password')
        
        if not login_val or not password:
            return Response(
                {"error": "Логин и пароль обязательны"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Аутентификация через наш бэкенд
        user = authenticate(request, login=login_val, password=password)
        
        if user is None:
            return Response(
                {"error": "Неверный логин или пароль"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Создаём сессию!
        login(request, user)
        
        return Response({
            "message": "Успешный вход",
            "user": CommissionMemberInfoSerializer(user).data
        }, status=status.HTTP_200_OK)


# --- Выход ---
class LogoutView(APIView):
    def post(self, request):
        logout(request)  # Удаляем сессию
        return Response({"message": "Успешный выход"}, status=status.HTTP_200_OK)


# --- Текущий пользователь ---
class CurrentUserView(APIView):
    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(CommissionMemberInfoSerializer(request.user).data)