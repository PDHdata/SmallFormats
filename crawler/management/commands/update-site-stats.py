from decklist.models import Deck, SiteStat
from ._command_base import LoggingBaseCommand


class Command(LoggingBaseCommand):
    help = 'Update site stats'

    def handle(self, *args, **options):
        super().handle(self, *args, **options)

        legal_decks = (
            Deck.objects
            .filter(pdh_legal=True)
            .count()
        )

        s = SiteStat(legal_decks=legal_decks)
        s.save()

        self._log(f"updated site stats; {str(s)}")
