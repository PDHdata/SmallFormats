from .models import Deck, Card, CardInDeck
from rest_framework import serializers


class CardSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Card
        fields = [
            'url', 'name',
        ]


class CardInDeckSerializer(serializers.HyperlinkedModelSerializer):
    card = CardSerializer()

    class Meta:
        model = CardInDeck
        fields = ['card', 'is_pdh_commander']


class DeckSerializer(serializers.HyperlinkedModelSerializer):
    card_list = CardInDeckSerializer(many=True)

    class Meta:
        model = Deck
        fields = [
            'url', 'name', 'source', 'source_link', 'creator_display_name',
            'ingested_time', 'updated_time', 'card_list',
        ]
