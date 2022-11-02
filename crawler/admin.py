from django.contrib import admin
from . import models


class DeckCrawlResultInline(admin.StackedInline):
    model = models.DeckCrawlResult

class CrawlRunAdmin(admin.ModelAdmin):
    inlines = (
        DeckCrawlResultInline,
    )

admin.site.register(models.CrawlRun, CrawlRunAdmin)
