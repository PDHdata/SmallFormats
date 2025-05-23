from decklist import views
from decklist.models import Theme
from django.urls import path
from .wubrg_utils import COLORS


urlpatterns = (
[
    path('', views.stats_index, name="index"),
    path('robots.txt', views.robots_txt, name="robots-txt"),
    path('about/', views.stats_index, {'page': 'stats/about.html'}, name="about"),
    path('privacy/', views.stats_index, {'page': 'stats/privacy.html'}, name="privacy"),
    path('versions/', views.versions, name="versions"),
    path('headers/', views.echo_headers, name="headers"),
    path('cmdr/', views.commander_index, name="cmdr"),
    path('land/', views.land_index, name="land"),
    path('card/', views.card_index, name="card"),
    path('theme/', views.theme_index, name="theme"),
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
    path('cmdr/background/', views.background_commanders, name="cmdr-background"),
    path('cmdr/partner/', views.partner_commanders, name="cmdr-partner"),
    path('cmdr/<uuid:cmdr_id>', views.single_cmdr, name="cmdr-single"),
    path('cmdr/<uuid:cmdr_id>/decks', views.single_cmdr_decklist, name="cmdr-decklist"),
    path('cmdr/<uuid:cmdr_id>/synergy', views.single_cmdr_synergy, name="cmdr-synergy-all"),
    path('cmdr/<uuid:cmdr_id>/synergy/<uuid:card_id>', views.synergy, name="cmdr-synergy-card"),
    path('card/top/nonland/', views.top_cards, kwargs={'include_land': False}, name="card-top-nonland"),
    path('card/top/', views.top_cards, name="card-top"),
    path('card/<uuid:card_id>', views.single_card, name="card-single"),
    path('card/<uuid:card_id>/synergy', views.single_card, kwargs={'sort_by_synergy': True}, name="card-single-synergy"),
    path('card/<uuid:card_id>/pairs', views.single_card_pairings, name="card-single-pairings"),
    path('card/<uuid:card_id>/setimage', views.set_editorial_image, name="card-setimage"),
    path('land/top/', views.top_lands, name="land-top"),
] +
[
    path(
        f'theme/{kind.label}/',
        views.theme_index,
        kwargs={'limit_to': kind},
        name=f"theme-{kind.label}",
    )
    for kind in Theme.Type
] +
[
    path('theme/<slug:theme_slug>/', views.single_theme, name="theme-single"),
    path('hx/cmdr/<int:cmdr_id>/<card_type>/<int:page_number>', views.hx_common_cards, name="hx-common-cards"),
    path('search/', views.search, name="search"),
])