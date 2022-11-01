from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models


class PrintingInline(admin.StackedInline):
    model = models.Printing

class CardAdmin(admin.ModelAdmin):
    inlines = (
        PrintingInline,
    )

admin.site.register(models.User, UserAdmin)
admin.site.register(models.Deck)
admin.site.register(models.Card, CardAdmin)
admin.site.register(models.CardInDeck)
