from django.urls import path

#views module import from current directory
from . import views
# from floraApp import views

urlpatterns = [
    path('', views.welcome, name="welcome"),
    path('login', views.login_view, name="login"),
    path('register', views.register_view, name="register"),
    path('home', views.home, name="home"),
    path('dashboard', views.dashboard_view, name="dashboard"),
    path('diagnose', views.diagnose_view, name="diagnose"),
    path('diagnosis/<int:pk>/cure/', views.mark_cured, name='mark_cured'),
    path('hh', views.hh_view, name="hh"),
    path('history', views.history_view, name="history"),
    path('profile', views.profile_view, name="profile"),
    path('diagnosis/<int:pk>/', views.diagnosis_detail, name='diagnosis_detail'),
    path('diagnosis/<int:pk>/pdf/', views.diagnosis_pdf, name="diagnosis_pdf"),
]
