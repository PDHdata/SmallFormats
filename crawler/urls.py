from crawler import views
from django.urls import path


app_name = 'crawler'
urlpatterns = [
    path('', views.crawler_index, name="index"),
    path('run/<int:run_id>/', views.run_detail, name="run-detail"),
    path('run/new/', views.new_run, name="run-new"),
]
