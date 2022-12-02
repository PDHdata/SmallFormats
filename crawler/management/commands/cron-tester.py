from django.core.management.base import BaseCommand, CommandError
from crawler.models import LogEntry
import time


class Command(BaseCommand):
    help = 'Test cron functionality'

    def handle(self, *args, **options):
        l1 = LogEntry(text="Starting run...")
        print(l1.text)
        l1.save()

        time.sleep(2)

        l2 = LogEntry(text="Finishing run.", follows=l1)
        print(l2.text)
        l2.save()
