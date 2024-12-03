from django.contrib import admin
from .models import User, Farmer, Produce, Order, Consumer, DeliveryPerson, Message

# Register your models here.
admin.site.register(User)
admin.site.register(Farmer)
admin.site.register(Produce)
admin.site.register(Consumer)


class OrderAdmin(admin.ModelAdmin):
    list_display = ('consumer', 'produce', 'status', 'delivery_person')
    fields = ('consumer', 'produce', 'quantity_ordered', 'total_price',
              'status', 'delivery_person', 'delivery_address', 'delivery_or_pickup')


admin.site.register(Order, OrderAdmin)

# Customize the DeliveryPerson admin view to include assigned orders
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ['user', 'contact_number']


# Customize the Message admin view
class MessageAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ['order', 'sender', 'content', 'timestamp']
    search_fields = ['sender__username', 'content']  # Add search functionality
    list_filter = ['timestamp']  # Add filter by timestamp


admin.site.register(Message, MessageAdmin)
admin.site.register(DeliveryPerson, DeliveryPersonAdmin)
