from django.contrib import admin
from . import models


admin.site.register(models.CrawlRun)
# this would be a nice inline if it were paginated
admin.site.register(models.DeckCrawlResult)
