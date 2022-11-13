from crawler import views
from django.urls import path


app_name = 'crawler'
urlpatterns = [
    path('', views.crawler_index, name="index"),
    path('run/<int:run_id>/', views.run_detail, name="run-detail"),
    path('run/<int:run_id>/clear', views.run_remove_error_hx, name="run-remove-error"),
    path('run/new/archidekt/', views.new_archidekt_run_hx, name="run-new-archidekt"),
]
