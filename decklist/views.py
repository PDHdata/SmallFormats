from .models import Deck, Card
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import CardSerializer, DeckSerializer


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
    queryset = Card.objects.all().order_by('name')
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]
