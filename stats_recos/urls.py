from stats_recos import views
from django.urls import path
from .wubrg_utils import COLORS


urlpatterns = (
[
    path('', views.stats_index, name="index"),
    path('cmdr/', views.commander_index, name="cmdr"),
    path('land/', views.land_index, name="land"),
] +
[
    path(f'cmdr/{name}/', views.commanders_by_color, filters, name=f'cmdr-{name}')
    for name, _, filters in COLORS
] +
[
    path(f'land/{name}/', views.lands_by_color, filters, name=f'land-{name}')
    for name, _, filters in COLORS
] +
[
    path('cmdr/top/', views.top_commanders, name="cmdr-top"),
    path('cards/top/', views.top_cards, name="top-cards"),
    path('land/top/', views.top_lands, name="land-top"),
    path('partner_decks/', views.partner_decks, name="partner-decks"),
])