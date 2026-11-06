from django.contrib import admin
from .models import Source, Document, Chunk
admin.site.register(Source)
admin.site.register(Document)
admin.site.register(Chunk)
