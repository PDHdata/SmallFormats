from django.db import models


class Rarity(models.TextChoices):
    COMMON = 'C', "common"
    UNCOMMON = 'U', "uncommon"
    RARE = 'R', "rare"
    SPECIAL = 'S', "special"
    MYTHIC = 'M', "mythic"
    BONUS = 'B', "bonus"
