from django import forms
from ..models import UserData

class UserDataForms(forms.ModelForm):
    class Meta:
        model=UserData
        fields=['name','email']