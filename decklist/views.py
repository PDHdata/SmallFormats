from .models import Deck, Card, DataSource
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import CardSerializer, DeckListSerializer, DeckInstanceSerializer
from django_filters import rest_framework as filters


class DeckFilter(filters.FilterSet):
    name = filters.CharFilter()
    ingested_time = filters.DateTimeFromToRangeFilter()
    updated_time = filters.DateTimeFromToRangeFilter()
    source = filters.ChoiceFilter(choices=DataSource.choices)


class DeckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing decks.
    """
    queryset = Deck.objects.all().order_by('-updated_time')
    serializer_class = DeckInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = DeckFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return DeckListSerializer
        return super().get_serializer_class()


class CardFilter(filters.FilterSet):
    name = filters.CharFilter()
    identity_w = filters.BooleanFilter(label='is W')
    identity_u = filters.BooleanFilter(label='is U')
    identity_b = filters.BooleanFilter(label='is B')
    identity_r = filters.BooleanFilter(label='is R')
    identity_g = filters.BooleanFilter(label='is G')
    ever_common = filters.BooleanFilter()
    ever_uncommon = filters.BooleanFilter()
    can_be_pdh_commander = filters.BooleanFilter(label='can be PDH commander')


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing cards.
    """
    queryset = Card.objects.all().order_by('name')
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = CardFilter