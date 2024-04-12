To take a backup:
1. Open a Fly proxy to the db server: `fly proxy 5434:5432 -a pdhdatapg`
2. Dump: `pg_dump -h localhost -p 5434 -U postgres pdhdata > backup_file`
