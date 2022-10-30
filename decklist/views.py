from .models import Deck, Card, CardInDeck
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import CardInDeckSerializer, CardSerializer, DeckSerializer


class DeckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing decks.
    """
    queryset = Deck.objects.all().order_by('-updated_time')
    serializer_class = DeckSerializer
    permission_classes = [permissions.IsAuthenticated]


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing cards.
    """
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]


class CardInDeckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for cards in a deck
    """
    queryset = CardInDeck.objects.all()
    serializer_class = CardInDeckSerializer
    permission_classes = [permissions.IsAuthenticated]
