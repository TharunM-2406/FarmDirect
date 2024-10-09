from django.db import models
from django.conf import settings  # Import settings for AUTH_USER_MODEL
from django.contrib.auth.models import AbstractUser
import json
import numpy as np

# Custom User model
class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_user = models.BooleanField(default=False)

    class Meta:
        swappable = 'AUTH_USER_MODEL'

# Model for Farmer


class Farmer(models.Model):
    # Use settings.AUTH_USER_MODEL
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    farm_name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=15)
    face_encoding = models.TextField(
        blank=True, null=True)  # Store face encoding as JSON

    def __str__(self):
        return self.farm_name

# Model for Produce
class Produce(models.Model):
    QUALITY_CHOICES = [
        ('Excellent', 'Excellent'),
        ('Good', 'Good'),
        ('Average', 'Average'),
    ]
    
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    image = models.ImageField(
        upload_to='produce_images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.farmer.farm_name}"

# Model for Orders
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    consumer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Use AUTH_USER_MODEL
    produce = models.ForeignKey(Produce, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.CharField(max_length=300, blank=True, null=True)
    delivery_or_pickup = models.CharField(max_length=10, choices=[('Delivery', 'Delivery'), ('Pickup', 'Pickup')])

    def __str__(self):
        return f"Order by {self.consumer.username} - {self.produce.name}"

# Model for Consumer Profile (optional, using built-in User model or extending)
class ConsumerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Use AUTH_USER_MODEL
    address = models.CharField(max_length=300)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username
