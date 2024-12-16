# audio/models.py
from django.db import models

class AudioFile(models.Model):
    audio = models.FileField(upload_to='audio/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name