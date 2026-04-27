# audio/auth_backends.py
from django.contrib.auth.backends import BaseBackend
from .models import CommissionMember

class CommissionMemberAuthBackend(BaseBackend):
    """
    Бэкенд для аутентификации через CommissionMember по логину/паролю
    """
    def authenticate(self, request, login=None, password=None, **kwargs):
        if login is None or password is None:
            return None
        
        try:
            member = CommissionMember.objects.get(login=login, is_active=True)
        except CommissionMember.DoesNotExist:
            return None
        
        if member.check_password(password):
            return member  # Возвращаем объект пользователя
        return None
    
    def get_user(self, user_id):
        try:
            return CommissionMember.objects.get(ID=user_id, is_active=True)
        except CommissionMember.DoesNotExist:
            return None