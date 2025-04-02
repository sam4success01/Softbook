from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.home, name='home'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('leave/', views.leave_list, name='leave_list'),
    path('leave/request/', views.leave_request, name='leave_request'),
    path('leave/<int:pk>/approve/', views.leave_approve, name='leave_approve'),
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/generate/', views.generate_payroll, name='generate_payroll'),
    path('performance/', views.performance_list, name='performance_list'),
    path('performance/review/<int:pk>/', views.performance_review, name='performance_review'),
    path('departments/', views.department_list, name='department_list'),
]