from ._command_base import LoggingBaseCommand
from django.core.management.base import CommandError
from decklist.models import Card, Rarity, SynergyScore
from decklist.synergy import compute_synergy_bulk
import math


class Command(LoggingBaseCommand):
    help = 'Compute card synergy scores'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--log-all', action='store_true')
        parser.add_argument('--card', type=str)

    def handle(self, *args, **options):
        super().handle(*args, **options)

        log_all = options['log_all']

        if log_all:
            self._log('Loudly computing card synergy scores')
        else:
            self._log('Computing card synergy scores')

        target_card = options['card']
        if target_card:
            # force high-fidelity logging to on since there's just one card
            log_all = True
            cards = (
                Card.objects
                .filter(name__iexact=target_card)
            )
            results = cards.count()
            if results > 1:
                self._err(f'{target_card} matches more than one card')
                raise CommandError(f'{target_card} matches more than one card')
            elif results == 0:
                self._err(f'{target_card} matches no cards')
                raise CommandError(f'{target_card} matches no cards')
        
        else:
            cards = (
                Card.objects
                .filter(
                    # skip cards never printed at common
                    printings__rarity=Rarity.COMMON,
                    deck_list__deck__pdh_legal=True,
                )
                .distinct()
            )

            # in the standard case, delete synergy scores for any
            # cards which have dropped out of decks
            deleted, _ = (
                SynergyScore.objects
                .exclude(card__in=cards)
                .delete()
            )
            if deleted > 0:
                self._log(f"Deleted {deleted} irrelevant scores")

        for card in cards:
            if log_all:
                self._log(f"Working on {card}")

            existing_scores = (
                SynergyScore.objects
                .filter(card=card)
            )

            new_records = []
            update_records = []
            skipped_records = 0

            scores = compute_synergy_bulk(card)
            for commander, score in scores:
                try:
                    score_record = existing_scores.get(commander=commander)
                    # if the score has changed, record it

                    # treat NaN and NULL as 0
                    old_score = score_record.score or 0.0
                    if math.isnan(old_score):
                        old_score = 0.0

                    if abs(score - old_score) >= 0.005:
                        score_record.score = score
                        update_records.append(score_record)
                    else:
                        skipped_records += 1
                except SynergyScore.DoesNotExist:
                    score_record = SynergyScore(commander=commander, card=card)
                    score_record.score = score
                    new_records.append(score_record)
                
            if len(new_records) > 0:
                SynergyScore.objects.bulk_create(new_records)
            if len(update_records) > 0:
                SynergyScore.objects.bulk_update(update_records, ['score',])
            
            if log_all:
                self._log(f"{len(new_records)} new scores, {len(update_records)} updated scores, {skipped_records} skipped")
            elif len(new_records) > 0 or len(update_records) > 0:
                self._log(f"{card}: {len(new_records)} new scores, {len(update_records)} updated scores, {skipped_records} skipped")

        self._log("Done!")
