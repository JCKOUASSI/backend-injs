from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='auth-login'),
    path('token/refresh/', views.CookieTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.logout_view, name='auth-logout'),
    path('me/', views.me_view, name='auth-me'),
    path('roles/', views.roles_view, name='auth-roles'),
    path('capabilities/', views.capabilities_view, name='auth-capabilities'),
    path('me/change-password/', views.change_password_view, name='auth-change-password'),
    path('users/', views.UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]
