from .models import Deck, Card, CardInDeck, DataSource
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


class DeckInstanceSerializer(serializers.HyperlinkedModelSerializer):
    card_list = CardInDeckSerializer(many=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['source'] = DataSource(ret['source']).label
        return ret

    class Meta:
        model = Deck
        fields = [
            'url', 'name', 'source', 'source_link', 'creator_display_name',
            'ingested_time', 'updated_time', 'card_list',
        ]


class DeckListSerializer(serializers.HyperlinkedModelSerializer):
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['source'] = DataSource(ret['source']).label
        return ret

    class Meta:
        model = Deck
        fields = [
            'url', 'name', 'source', 'source_link', 'creator_display_name',
            'ingested_time', 'updated_time',
        ]
