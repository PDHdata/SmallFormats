from ._command_base import LoggingBaseCommand
from django.core.management.base import CommandError
from django.db import transaction, connection
from decklist.models.card import TopCardView, TopLandCardView, TopNonLandCardView


class Command(LoggingBaseCommand):
    help = 'Compute top cards results'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        self._log("Computing top cards")

        with (
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            for model in (TopCardView, TopLandCardView, TopNonLandCardView):
                self._log(f"Refreshing {model._meta.db_table}")
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {model._meta.db_table};")

        self._log("Done!")
