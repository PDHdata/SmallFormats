from crawler import views
from django.urls import path


app_name = 'crawler'
urlpatterns = [
    path('', views.crawler_index, name="index"),
    path('fetchdeck/', views.fetch_deck_hx, name="fetch-deck"),
    path('fetchdeck/poll', views.start_deck_poll_hx, name="fetch-deck-poll"),
    path('run/<int:run_id>/', views.run_detail, name="run-detail"),
    path('run/<int:run_id>/cancel', views.run_cancel_hx, name="run-cancel"),
    path('run/<int:run_id>/clear', views.run_remove_error_hx, name="run-remove-error"),
    path('run/<int:run_id>/infinite', views.run_remove_limit_hx, name="run-remove-limit"),
    path('run/<int:run_id>/one', views.run_archidekt_onepage_hx, name="run-archidekt-one"),
    path('run/<int:run_id>/poll', views.start_archidekt_poll_hx, name="run-archidekt-poll"),
    path('run/new/archidekt/', views.new_archidekt_run_hx, name="run-new-archidekt"),
]
