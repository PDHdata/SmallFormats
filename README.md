# SmallFormats

Inspired by [EDHrec][edhrec], this is a deck-stats site for [Pauper EDH][pdhhomebase] and hopefully other "smaller" (less common) Magic: the Gathering formats someday.

## Fetching data

You will need card data from Scryfall and then a two-pass crawl of Archidekt.
The `crawl` step will fetch each deck, and then the `populate` step will fetch the decklists for each deck.

```shell
./manage fetch-cards
./manage crawl-archidekt
./manage populate-archidekt --crawl-id $ID_FROM_PREVIOUS_STEP
```

## Disclaimers & disclosures

SmallFormats is unofficial Fan Content permitted under WOTC's Fan Content Policy.
Not approved/endorsed by [Wizards][wotc].
Portions of the materials used are property of Wizards of the Coast.
©Wizards of the Coast LLC.

[Scryfall][scryfall] has not endorsed this app or its creators.
You should not have paid anything to anyone for its use.
You may not use Scryfall data to create new games, or to imply the information and images are from any other game besides Magic: The Gathering.

[Archidekt][archidekt] has not endorsed this app or its creators.

Thanks to Davis Haupt for the [fly.io deployment article][djangoonfly] which informed the layout of this project.

[archidekt]: https://www.archidekt.com/
[djangoonfly]: https://davi.sh/blog/2022/10/django-with-flyio/
[edhrec]: https://www.edhrec.com/
[pdhhomebase]: https://www.pdhhomebase.com/
[scryfall]: https://www.scryfall.com/
[wotc]: https://magic.wizards.com/
