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
    autocomplete_fields = ('commander',)
    list_display = ('name', 'pdh_legal')
    list_filter = ('pdh_legal',)


class CardInDeckAdmin(admin.ModelAdmin):
    search_fields = [
        'card__name',
    ]


class CommanderAdmin(admin.ModelAdmin):
    list_display = ('commander1', 'commander2')
    list_display_links = ('commander1', 'commander2')
    autocomplete_fields = ('commander1', 'commander2')
    search_fields = [
        'commander1__name',
        'commander2__name',
    ]


class ThemeAdmin(admin.ModelAdmin):
    list_display = (
        'display_name', 'filter_type', 'card_threshold', 'deck_threshold',
    )
    prepopulated_fields = {
        'slug': ('display_name',),
    }


class SynergyAdmin(admin.ModelAdmin):
    autocomplete_fields = ('card', 'commander')


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Deck, DeckAdmin)
admin.site.register(models.Card, CardAdmin)
admin.site.register(models.CardInDeck, CardInDeckAdmin)
admin.site.register(models.Printing, PrintingAdmin)
admin.site.register(models.SiteStat)
admin.site.register(models.Commander, CommanderAdmin)
admin.site.register(models.Theme, ThemeAdmin)
admin.site.register(models.SynergyScore, SynergyAdmin)
