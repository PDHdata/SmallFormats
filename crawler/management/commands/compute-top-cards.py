from ._command_base import LoggingBaseCommand
from django.core.management.base import CommandError
from django.db import transaction, connection
from decklist.models.card import TopCardView, TopLandCardView, TopNonLandCardView


# only Postgres has materialized views to refresh
from django.db import connections
WE_ARE_POSTGRES = True if connections['default'].vendor == 'postgresql' else False


class Command(LoggingBaseCommand):
    help = 'Compute top cards results'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        if not WE_ARE_POSTGRES:
            self._log("Non-Postgres database detected; nothing to do.")
            return

        self._log("Computing top cards")

        with (
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            for model in (TopCardView, TopLandCardView, TopNonLandCardView):
                self._log(f"Refreshing {model._meta.db_table}")
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {model._meta.db_table};")

        self._log("Done!")
