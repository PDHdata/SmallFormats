from stats_recos import views
from django.urls import path


urlpatterns = [
    path('top_cmdrs/', views.top_commanders, name="top-commanders"),
    path('top_cards/', views.top_cards, name="top-cards"),
    path('partner_decks/', views.partner_decks, name="partner-decks"),
]