from django.core.management.base import BaseCommand
from crawler.models import LogEntry


class LoggingBaseCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--no-db', action='store_true')
        parser.add_argument('--no-stdout', action='store_true')

    def handle(self, *args, **options):
        self._no_db = options.pop('no_db')
        self._no_stdout = options.pop('no_stdout')

    def _err(self, text):
        if not self._no_db:
            last_log = getattr(self, 'last_log', None)
            log = LogEntry(text=f"!!! {text}", follows=last_log)
            log.save()
            self.last_log = log
        if not self._no_stdout:
            self.stderr.write(text)
    
    def _log(self, text):
        if not self._no_db:
            last_log = getattr(self, 'last_log', None)
            log = LogEntry(text=text, follows=last_log)
            log.save()
            self.last_log = log
        if not self._no_stdout:
            self.stdout.write(text)
