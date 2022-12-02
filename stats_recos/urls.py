from stats_recos import views
from django.urls import path
from .wubrg_utils import COLORS


urlpatterns = (
[
    path('', views.stats_index, name="index"),
    path('about/', views.stats_index, {'page': 'stats/about.html'}, name="about"),
    path('privacy/', views.stats_index, {'page': 'stats/privacy.html'}, name="privacy"),
    path('cmdr/', views.commander_index, name="cmdr"),
    path('land/', views.land_index, name="land"),
    path('card/', views.card_index, name="card"),
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
    path(f'card/{name}/', views.cards_by_color, filters, name=f'card-{name}')
    for name, _, filters in COLORS
] +
[
    path('cmdr/top/', views.top_commanders, name="cmdr-top"),
    path('cmdr/bg/', views.top_commanders_background, name="cmdr-background"),
    path('cmdr/<uuid:card_id>', views.single_cmdr, name="cmdr-single"),
    path('cmdr/<uuid:card_id>/decks', views.single_cmdr_decklist, name="cmdr-decklist"),
    path('cmdr/<uuid:card_id>/partners', views.single_cmdr_partners, name="cmdr-partners"),
    path('card/top/', views.top_cards, name="card-top"),
    path('card/<uuid:card_id>', views.single_card, name="card-single"),
    path('card/<uuid:card_id>/setimage', views.set_editorial_image, name="card-setimage"),
    path('land/top/', views.top_lands, name="land-top"),
    path('partner_decks/', views.partner_decks, name="partner-decks"),
    path('hx/cmdr/<uuid:card_id>/<card_type>/<int:page_number>', views.hx_common_cards, name="hx-common-cards"),
    path('search/', views.search, name="search"),
])