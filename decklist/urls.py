from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'decks', views.DeckViewSet)
router.register(r'cards', views.CardViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
