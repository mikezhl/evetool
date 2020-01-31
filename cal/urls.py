from django.urls import path
from . import views

urlpatterns = [
    path('', views.init),
    path('get_info/', views.get_info),
    path('save/', views.save),
    path('start/<int:mode>/',views.start),

]