from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),

    # login/logout use Django's auth views; they render your templates
    path('login/',  auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # email verification / change email
    path('verify/<uuid:token>/', views.verify_email, name='verify_email'),
    path('request-verification/', views.request_verification, name='request_verification'),
    path('change-email/', views.change_email, name='change_email'),


]
