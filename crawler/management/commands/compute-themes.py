from ._command_base import LoggingBaseCommand
from django.db.models import Count, Q, F, Value
from django.core.management.base import CommandError
from decklist.models import Deck, Commander, Theme, ThemeResult


class Command(LoggingBaseCommand):
    help = 'Compute themes for commanders'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        self._log("Computing themes")

        for theme in Theme.objects.all():
            self._log(f"{theme}")
            theme_decks = self._get_decks_for_theme(theme)

            theme_cmdrs = (
                Commander.objects
                .annotate(
                    theme_decks=Count(
                        'decks',
                        filter=Q(decks__in=theme_decks),
                        unique=True,
                    ),
                    total_decks=Count('decks', unique=True),
                )
                .filter(theme_decks__gt=1)
                .filter(theme_decks__gte=F('total_decks') * Value(theme.deck_threshold / 100.0))
            )

            # add or update commanders
            for cmdr in theme_cmdrs:
                ThemeResult.objects.update_or_create(
                    theme=theme, commander=cmdr,
                    defaults={
                        'theme_deck_count': cmdr.theme_decks,
                        'total_deck_count': cmdr.total_decks,
                    }
                )
            
            # delete irrelevant commanders
            (
                ThemeResult.objects
                .filter(theme=theme)
                .exclude(commander__in=[cmdr for cmdr in theme_cmdrs])
                .delete()
            )

        self._log("Done!")

    def _get_decks_for_theme(self, theme):
        match theme.filter_type:
            case Theme.Type.TRIBE:
                return (
                        Deck.objects
                        .filter(pdh_legal=True)
                        .annotate(theme_count=Count(
                            'card_list',
                            filter=Q(card_list__card__type_line__contains=theme.filter_text),
                        ))
                        .filter(theme_count__gt=theme.card_threshold)
                    )

            case Theme.Type.KEYWORD:
                return (
                    Deck.objects
                    .filter(pdh_legal=True)
                    .annotate(keyword_count=Count(
                        'card_list',
                        filter=Q(card_list__card__keywords__contains=theme.filter_text),
                    ))
                    .filter(keyword_count__gt=theme.card_threshold)
                )

            case _:
                raise CommandError(f"Not prepared to handle a theme of type {theme.filter_type}")
