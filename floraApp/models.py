from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # link with User
    # full_name = models.CharField(max_length=100)
    # phone = models.CharField(max_length=15, blank=True, null=True)
    # address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

class Diagnosis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_name = models.CharField(max_length=100)
    symptoms = models.TextField()
    disease = models.CharField(max_length=100)
    cure = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    plant_image = models.ImageField(upload_to='diagnosis_images/', null=True, blank=True)
    is_cured = models.BooleanField(default=False)

def __str__(self):
    return f"{self.user.username} - {self.disease}"
