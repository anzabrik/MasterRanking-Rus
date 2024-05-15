from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(List)
admin.site.register(Author)
admin.site.register(Book)
admin.site.register(Book_In_List)
admin.site.register(Author_In_List)
admin.site.register(Master)
admin.site.register(Book_In_Master)
admin.site.register(Author_In_Master)