# audio/models.py
from django.db import models

class AudioFile(models.Model):
    audio = models.FileField(upload_to='audio/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
