from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models


admin.site.site_header = 'SmallFormats admin'
admin.site.site_title = 'SmallFormats admin'
admin.site.index_title = "SmallFormats aka PDHdata"

class PrintingInline(admin.StackedInline):
    model = models.Printing

class CardAdmin(admin.ModelAdmin):
    inlines = (
        PrintingInline,
    )
    search_fields = [
        'name',
    ]
    autocomplete_fields = [
        'editorial_printing',
    ]

class PrintingAdmin(admin.ModelAdmin):
    model = models.Printing

    search_fields = [
        'set_code', 'card__name',
    ]

class DeckAdmin(admin.ModelAdmin):
    search_fields = [
        'name', 'creator_display_name',
    ]

class CardInDeckAdmin(admin.ModelAdmin):
    search_fields = [
        'card__name',
    ]

admin.site.register(models.User, UserAdmin)
admin.site.register(models.Deck, DeckAdmin)
admin.site.register(models.Card, CardAdmin)
admin.site.register(models.CardInDeck, CardInDeckAdmin)
admin.site.register(models.Printing, PrintingAdmin)
admin.site.register(models.SiteStat)
