from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import UserProfile, Product, ProductImage, Category
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
    
    # Seller option
    is_seller = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Register as a seller/vendor'
    )
    seller_store_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your store name (required for sellers)'
        }),
        label='Store Name'
    )
    seller_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Describe your business (required for sellers)',
            'rows': 3
        }),
        label='Business Description'
    )

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
        
        # Validate seller fields
        is_seller = cleaned.get('is_seller')
        if is_seller:
            store_name = cleaned.get('seller_store_name', '').strip()
            description = cleaned.get('seller_description', '').strip()
            
            if not store_name:
                raise forms.ValidationError('Store name is required for sellers')
            if not description:
                raise forms.ValidationError('Business description is required for sellers')
            if len(store_name) < 3:
                raise forms.ValidationError('Store name must be at least 3 characters')
            if len(description) < 20:
                raise forms.ValidationError('Business description must be at least 20 characters')
        
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
        # Use get_or_create to avoid race condition with the post_save signal that also creates a profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        # Update profile fields
        profile.phone = data.get('phone_full', '')
        profile.is_seller = data.get('is_seller', False)
        profile.seller_store_name = data.get('seller_store_name', '')
        profile.seller_description = data.get('seller_description', '')
        # If seller, set application date
        if data.get('is_seller'):
            profile.seller_application_date = timezone.now()
        profile.save()
        
        # Create wallet will be handled elsewhere (view)
        return user


class ProductForm(forms.ModelForm):
    """Form for creating and editing products"""
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'stock', 'discount_percentage', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Product description',
                'rows': 5
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class ProductImageForm(forms.ModelForm):
    """Form for uploading product images"""
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'order']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '0'
            })
        }


class MultipleFileInput(forms.ClearableFileInput):
    """Widget that supports multiple file uploads and returns a list"""
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        # Return a list of files when multiple are uploaded
        if name in files:
            return files.getlist(name)
        return super().value_from_datadict(data, files, name)


class MultiFileField(forms.FileField):
    """Custom FileField to accept multiple uploaded files"""

    def to_python(self, data):
        # Normalize to a list of files
        if not data:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def validate(self, data):
        # Use Field.validate for required checks
        forms.Field.validate(self, data)
        # Data should be a list
        if not isinstance(data, (list, tuple)):
            raise forms.ValidationError('Invalid uploaded files')
        # Validate each file is an image
        for f in data:
            content_type = getattr(f, 'content_type', '')
            if content_type and not content_type.startswith('image'):
                raise forms.ValidationError('Only image files are allowed')


class MultipleProductImageForm(forms.Form):
    """Form for uploading multiple images at once"""
    images = MultiFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'multiple': True,
            'accept': 'image/*',
            'class': 'form-control'
        }),
        help_text='Select one or more image files'
    )