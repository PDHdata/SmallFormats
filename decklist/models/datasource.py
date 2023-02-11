from django.db import models


class DataSource(models.IntegerChoices):
    UNKNOWN_OTHER = 0, "Unknown/other"
    ARCHIDEKT = 1
    MOXFIELD = 2
