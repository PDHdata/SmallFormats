-- SQLite prototype for partners

.parameter init
.parameter set @CMDR "'a66f8b4401634456b1524acefab896a4'"

-- does not account for legal decks

select decklist_card.name, count(decklist_card.id) as paired_count
from decklist_deck
join decklist_cardindeck on decklist_deck.id=decklist_cardindeck.deck_id
join decklist_card on decklist_cardindeck.card_id=decklist_card.id
where decklist_deck.id in
(
  -- decks with > 1 commander
  select decklist_deck.id from decklist_deck
  join decklist_cardindeck on decklist_deck.id=decklist_cardindeck.deck_id
  group by decklist_deck.id
  having count(decklist_cardindeck.card_id)
    filter (where decklist_cardindeck.is_pdh_commander=1) > 1
  intersect
  -- decks where `a66f` is a commander
  select
    decklist_deck.id
  from decklist_deck
    join decklist_cardindeck on decklist_deck.id=decklist_cardindeck.deck_id
    where decklist_cardindeck.card_id = @CMDR
      and decklist_cardindeck.is_pdh_commander = 1
)
and decklist_cardindeck.is_pdh_commander=1
and decklist_cardindeck.card_id != @CMDR
group by decklist_card.id
order by paired_count desc;
