from django.core.management.base import BaseCommand, CommandError
from decklist.models import Deck


class Command(BaseCommand):
    help = 'Revalidate legality of decks'

    def handle(self, *args, **options):
        pre_check = Deck.objects.filter(pdh_legal=True).count()
        self.stdout.write(f"Pre-check: {pre_check} legal decks")

        for deck in Deck.objects.all():
            is_legal, reason = deck.check_deck_legality()
            if is_legal != deck.pdh_legal:
                self.stdout.write(f"{deck} {is_legal=} {reason=}")
                deck.pdh_legal = is_legal
                deck.save()

        post_check = Deck.objects.filter(pdh_legal=True).count()
        self.stdout.write(f"Post-check: {post_check} legal decks")
