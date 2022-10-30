from .models import Deck, Card, CardInDeck
from rest_framework import serializers


class DeckSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Deck
        fields = [
            'url', 'name', 'source', 'source_link', 'creator_display_name',
            'ingested_time', 'updated_time', 'card_list',
        ]


class CardSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Card
        fields = [
            'name',
        ]


class CardInDeckSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CardInDeck
        fields = ['card', 'deck', 'is_pdh_commander']