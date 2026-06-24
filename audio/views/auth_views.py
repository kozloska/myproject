from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..serializers import CommissionMemberSerializer
import logging

logger = logging.getLogger(__name__)

# ==================== LOGIN ====================
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  

    def post(self, request):

        login_val = request.data.get('login')
        password = request.data.get('password')

        if not login_val or not password:
            return Response({"error": "Логин и пароль обязательны"}, 
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, login=login_val, password=password)
        if user is None:
            logger.warning(f"Authentication FAILED for: {login_val}")
            return Response({"error": "Неверный логин или пароль"}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)

        return Response({
            "message": "Успешный вход",
            "user": CommissionMemberSerializer(user).data
        }, status=status.HTTP_200_OK)

# ==================== LOGOUT ====================
@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]      # ← Изменили на AllowAny
    authentication_classes = []  

    def post(self, request):
                
        # Если пользователь авторизован — выходим
        if request.user.is_authenticated:
            logout(request)
        else:
            logger.info("User was not authenticated")

        return Response({"message": "Успешный выход"}, status=status.HTTP_200_OK)

# ==================== CURRENT USER ====================
class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CommissionMemberSerializer(request.user).data)