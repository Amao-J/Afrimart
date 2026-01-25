from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import UserProfile
import re


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password'
        })
    )

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        password = cleaned.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError('Invalid username or password')
            cleaned['user'] = user
        return cleaned


class RegisterForm(forms.Form):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    country_code = forms.ChoiceField(
        choices=[('+234', '🇳🇬 Nigeria (+234)'), ('+27','🇿🇦 South Africa (+27)'), ('+254','🇰🇪 Kenya (+254)'), ('+233','🇬🇭 Ghana (+233)'), ('+1','🇺🇸 USA (+1)')],
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'country_code'})
    )
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '8012345678', 'id': 'phone'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'At least 6 characters', 'id': 'password1'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password', 'id': 'password2'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        phone_clean = re.sub(r'\D', '', phone)
        if phone_clean.startswith('0'):
            phone_clean = phone_clean[1:]
        if len(phone_clean) < 7:
            raise forms.ValidationError('Enter a valid phone number')
        return phone_clean

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match')
        if p1 and len(p1) < 6:
            raise forms.ValidationError('Password must be at least 6 characters')
        # Check phone uniqueness
        phone_clean = cleaned.get('phone')
        cc = cleaned.get('country_code', '+234')
        if phone_clean:
            phone_full = cc + phone_clean
            if UserProfile.objects.filter(phone=phone_full).exists():
                raise forms.ValidationError('Phone number already registered')
            cleaned['phone_full'] = phone_full
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        UserProfile.objects.create(user=user, phone=data.get('phone_full', ''))
        # Create wallet will be handled elsewhere (view)
        return user