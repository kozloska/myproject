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

class Institute(models.Model):
    ID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)

    class Meta:
        db_table = 'Institute'

    def __str__(self):
        return self.Name


class Group(models.Model):
    ID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=50)
    ID_Institute = models.ForeignKey(Institute, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Group'

    def __str__(self):
        return self.Name


class Student(models.Model):
    ID = models.AutoField(primary_key=True)
    Surname = models.CharField(max_length=50)
    Name = models.CharField(max_length=50)
    Patronymic = models.CharField(max_length=50)
    ID_Group = models.ForeignKey(Group, on_delete=models.CASCADE)
    ID_Specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    ID_Project = models.ForeignKey('Project', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'Student'

    def __str__(self):
        return f"{self.Surname} {self.Name} {self.Patronymic}"


class Project(models.Model):
    ID = models.AutoField(primary_key=True)
    Title = models.CharField(max_length=100)
    Supervisor = models.CharField(max_length=100)
    Status = models.BooleanField(default=False)

    class Meta:
        db_table = 'Project'

    def __str__(self):
        return self.Title


class Question(models.Model):
    ID = models.AutoField(primary_key=True)
    Text = models.TextField()
    ID_Project = models.ForeignKey(Project, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Question'

    def __str__(self):
        return self.Text


class Protocol(models.Model):
    ID = models.AutoField(primary_key=True)
    Year = models.IntegerField()
    Grade = models.CharField(max_length=10)
    ID_Question = models.ForeignKey(Question, on_delete=models.CASCADE)
    ID_Student = models.ForeignKey(Student, on_delete=models.CASCADE)
    ID_DefenseSchedule = models.ForeignKey('DefenseSchedule', on_delete=models.SET_NULL, null=True)
    DefenseStartTime = models.TimeField(blank=True, null=True)
    Number = models.CharField(max_length=30)

    class Meta:
        db_table = 'Protocol'




class DefenseSchedule(models.Model):
    ID = models.AutoField(primary_key=True)
    DateTime = models.DateTimeField()
    ID_Commission = models.ForeignKey('Commission', on_delete=models.CASCADE)
    class Meta:
        db_table = 'DefenseSchedule'

    def __str__(self):
        return f"{self.DateTime}"

class CommissionMember(models.Model):
    ID = models.AutoField(primary_key=True)
    Surname = models.CharField(max_length=50)
    Name = models.CharField(max_length=50)
    Patronymic = models.CharField(max_length=50)

    class Meta:
        db_table = 'CommissionMember'

    def __str__(self):
        return f"{self.Surname} {self.Name} {self.Patronymic}"


class CommissionComposition(models.Model):
    ID = models.AutoField(primary_key=True)
    ID_Commission = models.ForeignKey(Commission, on_delete=models.CASCADE)
    ID_Member = models.ForeignKey(CommissionMember, on_delete=models.CASCADE)
    Role = models.CharField(max_length=100)

    class Meta:
        db_table = 'CommissionComposition'

    def __str__(self):
        return f"{self.ID_Member} - {self.Role}"

class User(models.Model):
    id = models.AutoField(primary_key=True)  # SERIAL в PostgreSQL соответствует AutoField
    login = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    full_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'user'  # Указываем имя таблицы в базе данных




class SecretarySpecialization(models.Model):
    ID_Specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    ID_Secretary = models.ForeignKey(CommissionMember, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Secretary/Specialization'

    def __str__(self):
        return f"{self.ID_Specialization} - {self.ID_Secretary}"