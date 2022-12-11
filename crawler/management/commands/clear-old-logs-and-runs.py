from ._command_base import LoggingBaseCommand
from django.utils import timezone
from datetime import timedelta
from crawler.models import LogEntry, CrawlRun


class Command(LoggingBaseCommand):
    help = 'Clear old runs and logs'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--older-than', type=int, default=60)

    def handle(self, *args, **options):
        super().handle(*args, **options)
        age_days = options['older_than']
        before_datetime = timezone.now() - timedelta(days=age_days)
        before_date = before_datetime.date()
        precise_before_date = before_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        self._log(f"Clearing logs/runs before {before_date} ({age_days} days).")
        log_records, _ = (
            LogEntry.objects
            .filter(created__lt=precise_before_date)
            .delete()
        )
        run_records, _ = (
            CrawlRun.objects
            .filter(crawl_start_time__lt=precise_before_date)
            .delete()
        )
        self._log(f"Deleted {log_records} logs, {run_records} runs.")
