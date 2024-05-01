from django.contrib import admin
from . import models


class CrawlRunAdmin(admin.ModelAdmin):
    date_hierarchy = 'crawl_start_time'
    list_filter = ['target', 'state']
    search_fields = ['note']


class DeckCrawlResultAdmin(admin.ModelAdmin):
    date_hierarchy = 'updated_time'
    list_filter = ['fetchable', 'got_cards']


class LogStartAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    readonly_fields = ['text']
    search_fields = ['text']


class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'parent__created'
    list_filter = ['is_stderr']
    readonly_fields = ['text', 'is_stderr', 'parent']
    search_fields = ['text']


admin.site.register(models.CrawlRun, CrawlRunAdmin)
# this would be a nice inline if it were paginated
admin.site.register(models.DeckCrawlResult, DeckCrawlResultAdmin)
admin.site.register(models.LogStart, LogStartAdmin)
admin.site.register(models.LogEntry, LogEntryAdmin)
