from crawler import views
from django.urls import path


app_name = 'crawler'
urlpatterns = [
    path('', views.crawler_index, name="index"),
    path('logs/', views.log_index, name="log-index"),
    path('logs/<int:logstart_id>', views.log_one, name="log-one"),
    path('runs/', views.run_index, name="run-index"),
    path('runs/<int:run_id>/', views.run_detail, name="run-detail"),
    path('runs/<int:run_id>/cancel', views.run_cancel_hx, name="run-cancel"),
    path('runs/<int:run_id>/clear', views.run_remove_error_hx, name="run-remove-error"),
    path('runs/<int:run_id>/infinite', views.run_remove_limit_hx, name="run-remove-limit"),
    path('stats/', views.update_stats, name="update-stats"),
    path('tappedout/', views.tapped_out_page, name="tappedout_page"),
    path('tappedout/<int:page_number>/', views.tapped_out_page, name="tappedout_page"),
]
