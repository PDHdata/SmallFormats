from ._command_base import LoggingBaseCommand
from decklist.models import Deck, Commander


class Command(LoggingBaseCommand):
    help = 'Compute and store commanders/commander pairs'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--all', action='store_true')

    def handle(self, *args, **options):
        super().handle(*args, **options)

        query = Deck.objects.filter(pdh_legal=True)
        if options['all']:
            self._log('Re-computing all commanders for PDH-legal decks')
        else:
            self._log('Computing new commanders for PDH-legal decks')
            query = query.filter(commander__isnull=True)

        for deck in query:
            match list(deck.commander_cards()):
                case [commander1]:
                    cmdr, created = Commander.objects.get_or_create(
                        commander1=commander1.card,
                        commander2=None,
                    )
                    if created: self.stdout.write(f"created commander {cmdr}")
                    deck.commander = cmdr
                    deck.save()
                case [commander1, commander2]:
                    # commander1 should have an ID <= commander2's
                    if commander1.card.id > commander2.card.id:
                        commander1, commander2 = commander2, commander1
                    cmdr, created = Commander.objects.get_or_create(
                        commander1=commander1.card,
                        commander2=commander2.card,
                    )
                    if created: self.stdout.write(f"created commander {cmdr}")
                    deck.commander = cmdr
                    deck.save()
                case _:
                    self._err(f"{deck} ({deck.id}) has illegal number of commanders")
                    continue
        
        self._log("Done!")
