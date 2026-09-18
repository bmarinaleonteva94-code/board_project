from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Ad


class AdForm(forms.ModelForm):
    class Meta:
        model = Ad
        fields = ['title', 'description', 'price', 'category', 'contact', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Заголовок', 'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'Описание', 'rows': 5, 'class': 'form-input'
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': 'Цена (₽)', 'min': 0, 'class': 'form-input'
            }),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'contact': forms.TextInput(attrs={
                'placeholder': 'Телефон / email', 'class': 'form-input'
            }),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 5:
            raise forms.ValidationError('Заголовок должен быть не короче 5 символов')
        return title


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})