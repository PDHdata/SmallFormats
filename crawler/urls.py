from crawler import views
from django.urls import path


app_name = 'crawler'
urlpatterns = [
    path('', views.crawler_index, name="index"),
    path('logs/', views.log_index, name="log_index"),
    path('logs/<int:start_log>', views.log_from, name="log-from"),
    path('fetchdeck/', views.fetch_deck_hx, name="fetch-deck"),
    path('fetchdeck/poll', views.start_deck_poll_hx, name="fetch-deck-poll"),
    path('run/<int:run_id>/', views.run_detail, name="run-detail"),
    path('run/<int:run_id>/cancel', views.run_cancel_hx, name="run-cancel"),
    path('run/<int:run_id>/clear', views.run_remove_error_hx, name="run-remove-error"),
    path('run/<int:run_id>/infinite', views.run_remove_limit_hx, name="run-remove-limit"),
    path('archidekt/run/<int:run_id>/one', views.run_archidekt_onepage_hx, name="run-archidekt-one"),
    path('archidekt/run/<int:run_id>/poll', views.start_archidekt_poll_hx, name="run-archidekt-poll"),
    path('archidekt/run/new/', views.new_archidekt_run_hx, name="run-new-archidekt"),
    path('moxfield/run/<int:run_id>/one', views.run_moxfield_onepage_hx, name="run-moxfield-one"),
    path('moxfield/run/<int:run_id>/poll', views.start_moxfield_poll_hx, name="run-moxfield-poll"),
    path('moxfield/run/new/', views.new_moxfield_run_hx, name="run-new-moxfield"),
    path('stats/', views.update_stats, name="update-stats"),
]
