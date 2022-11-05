from stats_recos import views
from django.urls import path
from .wubrg_utils import COLORS


urlpatterns = (
[
    path('cmdr/', views.commander_colors, name="cmdr"),
] +
[
    path(f'cmdr/{name}/', views.commanders_by_color, filters, name=f'cmdr-{name}')
    for name, _, filters in COLORS
] +
[
    path('cmdr/top/', views.top_commanders, name="cmdr-top"),
    path('cards/top/', views.top_cards, name="top-cards"),
    path('lands/top/', views.top_lands, name="top-lands"),
    path('partner_decks/', views.partner_decks, name="partner-decks"),
])