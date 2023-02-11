from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Theme(models.Model):
    class Type(models.TextChoices):
        TRIBE = 'T', "tribal"
        KEYWORD = 'K', "keyword"
    
    display_name = models.CharField(
        max_length=30,
        help_text='Human-friendly theme name',
    )
    filter_text = models.CharField(
        max_length=30,
        help_text='String to match on cards',
    )
    filter_type = models.CharField(max_length=1, choices=Type.choices)
    slug = models.SlugField(unique=True)
    card_threshold = models.IntegerField(
        default=15,
        help_text='The minimum number of cards required in a deck to include it in the theme',
    )
    deck_threshold = models.SmallIntegerField(
        default=10,
        validators=(
            MinValueValidator(0),
            MaxValueValidator(100),
        ),
        help_text="The fraction of a commander's decks with this theme in order to say the commander has that theme",
    )

    def __str__(self):
        return f"{self.display_name} {self.get_filter_type_display()}"
