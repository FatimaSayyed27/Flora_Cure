from django.contrib import admin
from .models import Diagnosis
from .models import Profile

# Register your models here.
admin.site.register(Diagnosis)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'city', 'get_password')

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email Address'

    def get_password(self, obj):
        return obj.user.password   # Ye hashed password show karega
    get_password.short_description = 'Password'