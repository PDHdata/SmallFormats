from os import environ
import time

from django.core.management.base import BaseCommand, CommandError
import httpx


EXTERNAL_BASE_URL = 'https://api.machines.dev'
BASE_URL = environ['FLY_API_HOSTNAME'] if 'FLY_API_HOSTNAME' in environ else EXTERNAL_BASE_URL
BASE_API = "/v1/apps/pdhdata"
TOKEN = environ['FLY_API_TOKEN'] if 'FLY_API_TOKEN' in environ else None
RATE_LIMIT_DELAY = 1 # wait 1 second between calls


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--stop',
            action='store_const',
            const=True,
            default=None,
            help='Stop the machine',
        )
        parser.add_argument(
            '--start',
            action='store_const',
            const=True,
            default=None,
            help='Start the machine',
        )

    def handle(self, *args, **options):
        if not TOKEN:
            raise CommandError('missing API token: set FLY_API_TOKEN in the environment')

        self.stdout.write(f'using API at {BASE_URL}')
        headers = {
            'Authorization': f'Bearer {TOKEN}',
        }

        with httpx.Client(headers=headers) as client:
            self.stdout.write('locating machine')
            response = client.get(f"{BASE_URL}{BASE_API}/machines?metadata.fly_process_group=app")
            if not (200 <= response.status_code < 300):
                raise CommandError(f'failed to locate machine; got {response.status_code} {response.reason_phrase}')

            # ensure there's only one machine
            self.stdout.write('ensuring only one machine exists')
            machines = response.json()
            if len(machines) != 1:
                raise CommandError(f'expected 1 machine, got {len(machines)=}')
            
            machine_id, machine_instance_id = machines[0]["id"], machines[0]["instance_id"]
            self.stdout.write(f"{machine_id=} {machine_instance_id=}")

            # if neither --start nor --stop were specified, assume both
            if options['stop'] is None and options['start'] is None:
                options['stop'] = True
                options['start'] = True

            # stop the machine
            if options['stop']:
                time.sleep(RATE_LIMIT_DELAY)
                self.stdout.write('stopping the machine')
                response = client.post(f"{BASE_URL}{BASE_API}/machines/{machine_id}/stop", timeout=60.0)
                if not (200 <= response.status_code < 300):
                    raise CommandError(f'failed to stop machine; got {response.status_code} {response.reason_phrase}')

                # await its instance id to move to "stopped"
                time.sleep(RATE_LIMIT_DELAY)
                self.stdout.write('waiting for stop')
                response = client.get(f"{BASE_URL}{BASE_API}/machines/{machine_id}/wait?state=stopped&instance_id={machine_instance_id}")
                if not (200 <= response.status_code < 300):
                    raise CommandError(f'failed to await machine stoppage; got {response.status_code} {response.reason_phrase}')
            else:
                self.stdout.write('skipping machine stop')

            # start the machine
            if options['stop']:
                self.stdout.write('starting the machine')
                response = client.post(f"{BASE_URL}{BASE_API}/machines/{machine_id}/start")
                if not (200 <= response.status_code < 300):
                    raise CommandError(f'failed to start machine; got {response.status_code} {response.reason_phrase}')
            else:
                self.stdout.write('skipping machine start')
