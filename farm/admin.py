from django.contrib import admin
from .models import User, Farmer, Produce, Order, ConsumerProfile

# Register your models here.
admin.site.register(User)
admin.site.register(Farmer)
admin.site.register(Produce)
admin.site.register(Order)
admin.site.register(ConsumerProfile)
