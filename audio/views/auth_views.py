from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..serializers import CommissionMemberSerializer
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info("=== LOGIN ATTEMPT STARTED ===")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request cookies: {dict(request.COOKIES)}")
        logger.debug(f"Request data: {request.data}")

        login_val = request.data.get('login')
        password = request.data.get('password')

        if not login_val or not password:
            logger.warning("Missing login or password")
            return Response({"error": "Логин и пароль обязательны"}, 
                            status=status.HTTP_400_BAD_REQUEST)

        logger.debug(f"Trying to authenticate user: {login_val}")
        user = authenticate(request, login=login_val, password=password)

        if user is None:
            logger.warning(f"Authentication failed for user: {login_val}")
            return Response({"error": "Неверный логин или пароль"}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        logger.info(f"✅ SUCCESS: User {user.login} (ID={user.ID}) logged in")

        return Response({
            "message": "Успешный вход",
            "user": CommissionMemberSerializer(user).data
        }, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"Logout requested by user: {request.user}")
        logout(request)
        return Response({"message": "Успешный выход"}, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CommissionMemberSerializer(request.user).data)



