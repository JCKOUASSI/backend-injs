"""
Vues actives du dashboard Django.

Vues publiques / auth dans dashboard/urls.py :
  - login_view, logout_view, badge_view, qr_badge_privacy_view

Toutes les autres vues HTML (formations, participants, sessions…) ont été
remplacées par le frontend React. Elles sont archivées dans views_legacy.py.
"""
from functools import wraps

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect

User = get_user_model()

ALLOWED_WEB_ROLES = (
    'ADMIN',
    'DIRECTION',
    'CHEF_CPFAE_ADMIN',
    'CPFAE_ADMIN',
    'CHEF_SECRETARIAT',
    'SECRETARIAT',
    'ENCADRANT',
)


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated and request.user.role in ALLOWED_WEB_ROLES:
        return redirect('web-dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.role in ALLOWED_WEB_ROLES:
            login(request, user)
            return redirect('web-dashboard')
        elif user:
            return render(request, 'dashboard/login.html', {
                'error': 'Accès réservé à la Direction, CPFAE, Secrétariat et Encadrants.'
            })
        else:
            return render(request, 'dashboard/login.html', {
                'error': 'Identifiants invalides.'
            })
    return render(request, 'dashboard/login.html')


def logout_view(request):
    logout(request)
    return redirect('web-login')


def badge_view(request):
    """Page publique de badgeage — pas de login requis."""
    return render(request, 'dashboard/badge.html')


def qr_badge_privacy_view(request):
    """Politique de confidentialité (app mobile QR Badge) — publique, pour URL Play Console / App Store."""
    return render(request, 'dashboard/qr_badge_privacy.html')
