from django.urls import path
from . import views

urlpatterns = [
    path('', views.init),
    path('cal_init/',views.cal_init),
    path('main/<int:mode>/',views.main),

]