from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('pay/<slug:plan_slug>/', views.initiate_payment, name='initiate'),
    path('verify/', views.verify_payment, name='verify'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
]