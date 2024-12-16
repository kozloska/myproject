# audio/models.py
from django.db import models


class AudioFile(models.Model):
    audio = models.FileField(upload_to='audio/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Specialization(models.Model):
    ID = models.AutoField(primary_key=True)  # Используйте AutoField для ID
    Name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'Specialization'  # Укажите имя таблицы

    def __str__(self):
        return self.Name

class Commission(models.Model):
    ID = models.AutoField(primary_key=True)  # Используйте AutoField для ID
    Name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'Commission'  # Укажите имя таблицы

    def __str__(self):
        return self.Name

