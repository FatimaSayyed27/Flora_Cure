from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    new_password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    city = forms.CharField(required=False)

    class Meta:
        model = Profile
        fields = ['city']
