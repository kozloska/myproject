from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..serializers import CommissionMemberSerializer
import logging

logger = logging.getLogger(__name__)

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        login_val = request.data.get('login')
        password = request.data.get('password')

        logger.debug(f"Login attempt for user: {login_val}")

        if not login_val or not password:
            return Response({"error": "Логин и пароль обязательны"}, 
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, login=login_val, password=password)
        if user is None:
            logger.warning(f"Failed login for {login_val}")
            return Response({"error": "Неверный логин или пароль"}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        logger.info(f"User {user.login} logged in successfully")

        return Response({
            "message": "Успешный вход",
            "user": CommissionMemberSerializer(user).data
        }, status=status.HTTP_200_OK)

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"User {request.user} logging out")
        logout(request)
        return Response({"message": "Успешный выход"}, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CommissionMemberSerializer(request.user).data)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CommissionMemberSerializer(request.user).data)
