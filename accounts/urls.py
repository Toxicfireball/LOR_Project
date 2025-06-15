# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
        path('submissions/',                     views.submission_list, name='submission_list'),
    path('submit/<str:app_label>/<str:model_name>/new/',
         views.submit_model, name='submit_model'),
    path('submit/<str:app_label>/<str:model_name>/<int:pk>/',
         views.submit_model, name='edit_submission'),
]
