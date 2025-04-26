from django import forms
from .models import StudentRequest, StudentProfile
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib.auth.models import User


class StudentRequestForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class StudentProfileForm(forms.ModelForm):
    bio = forms.CharField(widget=CKEditorUploadingWidget, required=False)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = StudentProfile
        fields = ['bio', 'profile_picture', 'first_name', 'last_name', 'slug']

    def __init__(self, *args, **kwargs):
        user = kwargs.get('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.instance.user:
            self.instance.user.first_name = self.cleaned_data['first_name']
            self.instance.user.last_name = self.cleaned_data['last_name']
            self.instance.user.save()
        if commit:
            profile.save()
        return profile