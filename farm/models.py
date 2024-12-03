from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Custom User model
class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_farmer = models.BooleanField(default=False)
    is_consumer = models.BooleanField(default=False)

    class Meta:
        swappable = 'AUTH_USER_MODEL'

# Model for Farmer
class Farmer(models.Model):
    # One-to-one relation to User with `is_farmer` attribute
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    farm_name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=15)
    face_encoding = models.TextField(
        blank=True, null=True)  # Store face encoding as JSON

    def __str__(self):
        return f"Farmer: {self.user.username} - {self.farm_name}"

# Model for Consumer
class Consumer(models.Model):
    # One-to-one relation to User with `is_consumer` attribute
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.CharField(max_length=300)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return f"Consumer: {self.user.username}"

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

# DeliveryPerson model for managing delivery personnel accounts


class DeliveryPerson(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username


# Message model for chat between consumer and delivery person


class Message(models.Model):
    order = models.ForeignKey(
        'Order', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Message from {self.sender.username} on {self.timestamp}"

# Update Order model to include delivery status


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
    ]
    consumer = models.ForeignKey('Consumer', on_delete=models.CASCADE)
    produce = models.ForeignKey('Produce', on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='Pending')
    delivery_person = models.ForeignKey(
        'DeliveryPerson', on_delete=models.SET_NULL, null=True, blank=True)  # Ensure null=True and blank=True
    delivery_address = models.CharField(max_length=300, blank=True, null=True)
    delivery_or_pickup = models.CharField(
        max_length=10, choices=[('Delivery', 'Delivery'), ('Pickup', 'Pickup')]
    )

    def __str__(self):
        return f"Order by {self.consumer.user.username} - {self.produce.name}"
