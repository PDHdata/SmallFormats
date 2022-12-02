from django.core.management.base import BaseCommand, CommandError
from decklist.models import Deck


class Command(BaseCommand):
    help = 'Revalidate legality of decks'

    def handle(self, *args, **options):
        for deck in Deck.objects.all():
            is_legal, reason = deck.check_deck_legality()
            if is_legal != deck.pdh_legal:
                self.stdout.write(f"{deck} {is_legal=} {reason=}")
                deck.pdh_legal = is_legal
                deck.save()

