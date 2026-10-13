from django.urls import path

from . import views

app_name = 'betting'

urlpatterns = [
    path('picks/', views.picks, name='picks'),
    path('results/', views.results, name='results'),
]