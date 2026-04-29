# audio/auth_backends.py
from django.contrib.auth.backends import BaseBackend
from .models import CommissionMember
import logging

logger = logging.getLogger(__name__)

class CommissionMemberAuthBackend(BaseBackend):
    def authenticate(self, request, login=None, password=None, **kwargs):
        if login is None or password is None:
            return None
        
        try:
            member = CommissionMember.objects.get(login=login, is_active=True)
        except CommissionMember.DoesNotExist:
            logger.debug(f"User with login {login} not found")
            return None
        
        if member.check_password(password):
            logger.debug(f"Password correct for user {login}")
            return member
        
        logger.debug(f"Password incorrect for user {login}")
        return None

    def get_user(self, user_id):
        try:
            return CommissionMember.objects.get(ID=user_id, is_active=True)
        except CommissionMember.DoesNotExist:
            return None