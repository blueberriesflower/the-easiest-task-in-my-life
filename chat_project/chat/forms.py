from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Chat, Message
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class LoginForm(AuthenticationForm):
    """
    Форма входа пользователя.
    """
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ChatCreateForm(forms.ModelForm):
    """
    Форма создания нового чата.
    """
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Chat
        fields = ['name', 'members', 'is_group']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_group': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MessageForm(forms.ModelForm):
    """
    Форма отправки сообщения.
    """
    class Meta:
        model = Message
        fields = ['text', 'media']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите сообщение...'
            }),
            'media': forms.FileInput(attrs={'class': 'form-control'}),
        }
