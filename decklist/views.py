from .models import Deck, Card
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import CardSerializer, DeckListSerializer, DeckInstanceSerializer


class DeckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing decks.
    """
    queryset = Deck.objects.all().order_by('-updated_time')
    serializer_class = DeckInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DeckListSerializer
        return super().get_serializer_class()


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing cards.
    """
    queryset = Card.objects.all().order_by('name')
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]
