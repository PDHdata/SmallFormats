from ._command_base import LoggingBaseCommand
from decklist.models import Card, Commander, SynergyScore
from stats_recos.synergy import compute_synergy
import math


class Command(LoggingBaseCommand):
    help = 'Compute card synergy scores'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        commanders = Commander.objects.all()

        for commander in commanders:
            self._log(f"Working on {commander}")
            
            cards = (
                Card.objects
                .filter(deck_list__deck__commander=commander)
                .distinct()
                .exclude(id=commander.commander1.id)
            )
            if commander.commander2:
                cards = cards.exclude(id=commander.commander2.id)

            # delete synergy scores for any cards which have
            # dropped out of decks
            deleted, _ = (
                SynergyScore.objects
                .filter(commander=commander)
                .exclude(card__in=cards)
                .delete()
            )
            if deleted > 0:
                self._log(f"Deleted {deleted} irrelevant scores")

            existing_scores = (
                SynergyScore.objects
                .filter(commander=commander)
            )

            new_records = []
            update_records = []

            for card in cards:
                score = compute_synergy(commander, card)
                try:
                    score_record = existing_scores.get(card=card)
                    update_records.append(score_record)
                except SynergyScore.DoesNotExist:
                    score_record = SynergyScore(commander=commander, card=card)
                    new_records.append(score_record)
                
                score_record.score = score
            
            SynergyScore.objects.bulk_create(new_records)
            SynergyScore.objects.bulk_update(update_records, ['score',])
            self._log(f"{len(new_records)} new scores, {len(update_records)} updated scores")
        
        self._log("Done!")
