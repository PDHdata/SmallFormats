from django.core.management.base import BaseCommand
from crawler.models import LogStart, LogEntry


class LoggingBaseCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--no-db', action='store_true')
        parser.add_argument('--no-stdout', action='store_true')

    def handle(self, *args, **options):
        self._no_db = options.pop('no_db')
        self._no_stdout = options.pop('no_stdout')

    def _err(self, text):
        if not self._no_db:
            log_start = getattr(self, 'log_start', None)
            if log_start is None:
                log_start = self.log_start = LogStart(text=text)
                log_start.save()
            log = LogEntry(text=text, is_stderr=True, parent=log_start)
            log.save()
        if not self._no_stdout:
            self.stderr.write(text)
    
    def _log(self, text):
        if not self._no_db:
            log_start = getattr(self, 'log_start', None)
            if log_start is None:
                log_start = self.log_start = LogStart(text=text)
                log_start.save()
            log = LogEntry(text=text, parent=log_start)
            log.save()
        if not self._no_stdout:
            self.stdout.write(text)
