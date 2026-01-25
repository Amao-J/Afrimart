# main/auth_views.py
# Updated authentication views with international phone number support

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .models import Wallet
import re


def register_view(request):
    """User registration with international phone number (uses RegisterForm)"""
    if request.user.is_authenticated:
        return redirect('home')

    from .forms import RegisterForm

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    Wallet.objects.create(user=user, balance=0)
                    login(request, user)
                    messages.success(request, f"Welcome {user.first_name}! Your account has been created.")
                    return redirect('home')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            # Show form errors
            for err in form.errors.values():
                messages.error(request, err.as_text())
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    """User login (uses LoginForm)"""
    if request.user.is_authenticated:
        return redirect('home')

    from .forms import LoginForm

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)

            # Ensure wallet exists
            if not hasattr(user, 'wallet'):
                Wallet.objects.create(user=user, balance=0)

            # Ensure profile exists
            if not hasattr(user, 'profile'):
                from .models import UserProfile
                UserProfile.objects.create(user=user, phone='')

            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_page = request.GET.get('next', 'home')
            return redirect(next_page)
        else:
            for err in form.errors.values():
                messages.error(request, err.as_text())
    else:
        form = LoginForm()

    return render(request, 'main/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile with international phone number"""
    from .models import Order, UserProfile
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get user's wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get recent orders
    recent_orders = Order.objects.filter(buyer=request.user).order_by('-created_at')[:5]
    
    if request.method == 'POST':
        # Update profile
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        country_code = request.POST.get('country_code', '+234').strip()
        
        # Validate and format phone
        if phone:
            phone_cleaned = re.sub(r'\D', '', phone)
            if phone_cleaned.startswith('0'):
                phone_cleaned = phone_cleaned[1:]
            
            if not country_code.startswith('+'):
                country_code = '+' + country_code
            
            phone_formatted = country_code + phone_cleaned
            
            # Check if phone is taken by another user
            existing = UserProfile.objects.filter(phone=phone_formatted).exclude(user=request.user).exists()
            if existing:
                messages.error(request, 'Phone number already registered to another account')
            else:
                profile.phone = phone_formatted
                profile.save()
                messages.success(request, 'Profile updated successfully')
        
        # Update user
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()
        
        return redirect('profile')
    
    context = {
        'profile': profile,
        'wallet': wallet,
        'recent_orders': recent_orders
    }
    return render(request, 'main/profile.html', context)