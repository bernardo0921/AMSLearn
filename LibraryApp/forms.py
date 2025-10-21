from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import modelformset_factory
from .models import Course, Video


class CustomSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'placeholder': field.label
            })


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'thumbnail']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
            'placeholder': 'Enter course title'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
            'placeholder': 'Enter a short description',
            'rows': 4
        })
        self.fields['thumbnail'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
        })


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'video_file', 'description']  # Removed 'order' - it's set automatically in the view
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-african-lime focus:border-transparent transition',
                'placeholder': 'e.g., Introduction to Variables'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-african-lime focus:border-transparent transition',
                'placeholder': 'Brief description of what this video covers...',
                'rows': 3
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-african-lime focus:border-transparent transition',
                'accept': 'video/*'
            })
        }


VideoFormSet = modelformset_factory(
    Video, 
    form=VideoForm, 
    extra=1, 
    can_delete=False  # Changed to False since your template doesn't handle deletion
)