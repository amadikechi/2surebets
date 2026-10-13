from django.urls import path

from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('pricing/', views.pricing, name='pricing'),
]