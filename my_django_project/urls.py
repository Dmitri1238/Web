# my_django_project/urls.py
from django.contrib import admin
from django.urls import path, include
from main import views

urlpatterns = [
    path('admin/payment-request/<int:request_id>/approve/', views.approve_payment_request, name='approve_payment_request'),
    path('admin/payment-request/<int:request_id>/reject/', views.reject_payment_request, name='reject_payment_request'),
    path('admin/requests/', views.admin_payment_requests_view, name='admin_payment_requests'),  # Ваш маршрут
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]