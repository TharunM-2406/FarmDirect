from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import *
from django.utils import timezone
from django.contrib.auth import get_user_model
import re

User = get_user_model()

def home(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        # password2 = request.POST['password2']

        if len(username) < 6:
            messages.error(request, "Username must be at least 6 characters long")
            return redirect('register')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Invalid email address")
            return redirect('register')

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken")
            return redirect('register')

        user = User.objects.create_user(
            username=username, email=email, password=password1)
        user.save()
        return redirect('home')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')