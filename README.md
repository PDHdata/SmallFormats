# SmallFormats

Inspired by [EDHrec][edhrec], this is a deck-stats tool for [Pauper EDH][pdhhomebase] and hopefully other "smaller" (less common) Magic: the Gathering formats someday.
It was built to power [PDHdata][pdhdata], which is a deck-stats site specifically for PDH.

## Running your own

### Naming
This software is offered to you under the [MIT license](LICENSE).
That means you may use some or all of it to run your own project.
However, you don't have the right to the name `SmallFormats` or `PDHdata`.
You'll need to set an environment variable `SMALLFORMATS_NAME` or edit the config in `smallformats/settings.py` to whatever you're choosing to call your project.

### Database setup
_Unlike_ many Django projects, this one doesn't use SQLite locally.
We depend on several Postgres-specific features (materialized views, JSON field features, etc.).
While we **love** SQLite, it was becoming burdensome to support dev-only hacks mirroring Postgres features.
So as of now, we only support [Postgres](https://postgresql.org).
At time of writing (2024-11-26), we're using Postgres 15 in production.

For local dev work on my Mac, I've found [Postgres.app](https://postgresapp.com/) to work well.
You can either create a database called `pdhdev` or pass a `DATABASE_URL` with appropriate details every time you call `./manage`.

### Initial setup
It's a Django project managed with uv. For local dev, it's mostly the usual cycle of commands (though I've added a `./manage` shell script so you can avoid typing `uv run ./manage.py` all the time).


```shell
uv sync
./manage migrate
./manage createsuperuser
./manage runserver
```

### Fetching data
You will need card data from Scryfall and then a two-pass crawl of Archidekt.
The `crawl` step will fetch each deck, and then the `populate` step will fetch the decklists for each deck.

```shell
./manage fetch-cards
./manage crawl-archidekt
./manage populate-archidekt --crawl-id $ID_FROM_PREVIOUS_STEP
```

To fetch from Moxfield, you'll need to ask them nicely.
If approved, they'll set you up with an API key in the form of a specific user-agent.
Put your API key into the `SMALLFORMATS_MOXFIELD_USERAGENT` variable, otherwise you'll get a 403.

### Deploying to production
That part is up to you!

An incomplete list of steps required:
- Get a fly.io account
- Run Postgres in that fly.io account
- Deploy the app
- Set the `DATABASE_URL` and `SMALLFORMATS_MOXFIELD_USERAGENT` secrets
- Set the `FLY_API_HOST` and `FLY_API_TOKEN` secrets

## Disclaimers & disclosures

SmallFormats is unofficial Fan Content permitted under WOTC's Fan Content Policy.
Not approved/endorsed by [Wizards][wotc].
Portions of the materials used are property of Wizards of the Coast.
©Wizards of the Coast LLC.

[Scryfall][scryfall] has not endorsed this app or its creators.
You should not have paid anything to anyone for its use.
You may not use Scryfall data to create new games, or to imply the information and images are from any other game besides Magic: The Gathering.

[Archidekt][archidekt] and [Moxfield][moxfield] have not endorsed this app or its creators.

Thanks to Davis Haupt for the [fly.io deployment article][djangoonfly] which informed the layout of this project.

[archidekt]: https://www.archidekt.com/
[moxfield]: https://www.moxfield.com/
[djangoonfly]: https://davi.sh/blog/2022/10/django-with-flyio/
[edhrec]: https://www.edhrec.com/
[pdhdata]: https://pdhdata.com/
[pdhhomebase]: https://www.pdhhomebase.com/
[scryfall]: https://www.scryfall.com/
[wotc]: https://magic.wizards.com/
