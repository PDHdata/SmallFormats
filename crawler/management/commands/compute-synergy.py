from ._command_base import LoggingBaseCommand
from decklist.models import Card, SynergyScore
from stats_recos.synergy import compute_synergy_bulk


class Command(LoggingBaseCommand):
    help = 'Compute card synergy scores'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        self._log('Computing card synergy scores')

        cards = (
            Card.objects
            .filter(deck_list__deck__pdh_legal=True)
            .distinct()
        )

        # delete synergy scores for any cards which have
        # dropped out of decks
        deleted, _ = (
            SynergyScore.objects
            .exclude(card__in=cards)
            .delete()
        )
        if deleted > 0:
            self._log(f"Deleted {deleted} irrelevant scores")

        for card in cards:
            self._log(f"Working on {card}")

            existing_scores = (
                SynergyScore.objects
                .filter(card=card)
            )

            new_records = []
            update_records = []

            scores = compute_synergy_bulk(card)
            for commander, score in scores:
                try:
                    score_record = existing_scores.get(commander=commander)
                    update_records.append(score_record)
                except SynergyScore.DoesNotExist:
                    score_record = SynergyScore(commander=commander, card=card)
                    new_records.append(score_record)
                
                score_record.score = score

            SynergyScore.objects.bulk_create(new_records)
            SynergyScore.objects.bulk_update(update_records, ['score',])
            self._log(f"{len(new_records)} new scores, {len(update_records)} updated scores")

        self._log("Done!")
