from django.core.management.base import BaseCommand
from crawler.models import LogEntry


class LoggingBaseCommand(BaseCommand):
    def _err(self, text):
        last_log = getattr(self, 'last_log', None)
        log = LogEntry(text=f"!!! {text}", follows=last_log)
        log.save()
        self.last_log = log
        self.stderr.write(log.text)
    
    def _log(self, text):
        last_log = getattr(self, 'last_log', None)
        log = LogEntry(text=text, follows=last_log)
        log.save()
        self.last_log = log
        self.stdout.write(log.text)
