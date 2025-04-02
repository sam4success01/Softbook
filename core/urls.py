from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),  # Landing page
    path('dashboard/', views.dashboard, name='dashboard'),  # Main dashboard
]