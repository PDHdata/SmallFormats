To take a backup:
1. Open a Fly proxy to the db server: `fly proxy 5434:5432 -a pdhdatapg`
2. Dump: `pg_dump -h localhost -p 5434 -U postgres pdhdata > backup_file`

To restore a backup:
1. Open a Fly proxy to the db server: `fly proxy 5434:5432 -a pdhdatapg`
2. Make sure the database and role are created (locally, use `createdb -T template0 dbname` then log in to the database and `create role pdhdata`)
3. Restore: `psql -h localhost -p 5434 -U postgres pdhdata < backup_file`
