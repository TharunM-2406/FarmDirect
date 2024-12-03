from scipy.spatial import distance
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import *
from django.utils import timezone
from django.contrib.auth import get_user_model
import re
from django.db import IntegrityError
from .models import Produce, Order, Farmer
from django.http import HttpResponse
from django.http import JsonResponse
import stripe
from django.urls import reverse
import uuid
import face_recognition
import numpy as np
import cv2
from io import BytesIO
from face_recognition import face_encodings, compare_faces
from PIL import Image
import json
import base64
from django.core.files.base import ContentFile

User = get_user_model()

def home(request):
    return render(request, 'index.html')


# Register view for Consumer
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']

        if len(username) < 3:
            messages.error(
                request, "Username must be at least 3 characters long")
            return redirect('register')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, "Invalid email address")
            return redirect('register')

        if len(password1) < 8:
            messages.error(
                request, "Password must be at least 8 characters long")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken")
            return redirect('register')

        user = User.objects.create_user(
            username=username, email=email, password=password1)
        user.is_consumer = True
        user.save()

        # Create Consumer profile linked to User
        Consumer.objects.create(user=user, address='', contact_number='')

        return redirect('register')

    return render(request, 'register.html')

# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'login.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('home')

# Farmer signup view
def farmer_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        farm_name = request.POST['farm_name']
        location = request.POST['location']
        contact_number = request.POST['contact_number']
        face_image_data = request.POST.get('face_image', None)

        if password != confirm_password:
            messages.error(request, "Passwords don't match!")
            return redirect('farmer_signup')

        try:
            # Create the farmer user
            user = User.objects.create_user(
                username=username, password=password)
            user.is_farmer = True
            user.save()

            # Decode the base64 face image and get encoding
            if face_image_data:
                format, imgstr = face_image_data.split(';base64,')
                ext = format.split('/')[-1]
                face_image = ContentFile(base64.b64decode(
                    imgstr), name=f'{username}_face.{ext}')
                img_array = face_recognition.load_image_file(face_image)
                face_encodings = face_recognition.face_encodings(img_array)

                if len(face_encodings) > 0:
                    face_encoding_json = json.dumps(face_encodings[0].tolist())
                else:
                    messages.error(
                        request, "No face detected, please try again.")
                    return redirect('farmer_signup')
            else:
                messages.error(
                    request, "No face image provided, please capture your face.")
                return redirect('farmer_signup')

            # Save the Farmer profile linked to User
            farmer = Farmer(
                user=user,
                farm_name=farm_name,
                location=location,
                contact_number=contact_number,
                face_encoding=face_encoding_json  # Store the face encoding JSON
            )
            farmer.save()

            messages.success(request, "Farmer registered successfully!")
            return redirect('farmer_login')
        except IntegrityError:
            messages.error(request, "Username already taken!")
            return redirect('farmer_signup')

    return render(request, 'farmer_signup.html')


def farmer_login(request):
    if request.method == 'POST':
        # Check if the request is for face recognition login
        if 'face_image' in request.POST:
            try:
                # Decode the base64 face image data
                face_image_data = request.POST.get('face_image')
                face_image_data = face_image_data.split(',')[1]
                face_image_bytes = base64.b64decode(face_image_data)

                # Load the image and convert to RGB if necessary
                image = Image.open(BytesIO(face_image_bytes))
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # Convert image to a numpy array and extract face encodings
                image_array = np.array(image)
                face_encodings_list = face_recognition.face_encodings(
                    image_array)

                if len(face_encodings_list) == 0:
                    return JsonResponse({'success': False, 'message': 'No face detected. Please try again.'})

                face_encoding = face_encodings_list[0]

                # Retrieve all farmers with stored face encodings
                farmers = Farmer.objects.exclude(face_encoding__isnull=True)
                best_match = None
                best_distance = float('inf')

                # Compare face encodings with each farmer's stored encoding
                for farmer in farmers:
                    if farmer.face_encoding:
                        stored_encoding = np.array(
                            json.loads(farmer.face_encoding))
                        dist = distance.euclidean(
                            stored_encoding, face_encoding)
                        if dist < best_distance:
                            best_distance = dist
                            best_match = farmer

                # Set a threshold to consider a match valid (adjust as necessary)
                if best_match and best_distance < 0.5:  # Lower threshold for higher accuracy
                    login(request, best_match.user)
                    return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})
                else:
                    return JsonResponse({'success': False, 'message': 'Face ID not found'})

            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

        # Traditional username/password login
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'farmer') and user.farmer:
                login(request, user)
                return redirect('farmer_dashboard')
            else:
                messages.error(request, "You are not authorized as a farmer.")
                return redirect('farmer_login')
        else:
            messages.error(request, "Invalid credentials.")
            return redirect('farmer_login')

    return render(request, 'farmer_login.html')


# Farmer logout view
def farmer_logout(request):
    logout(request)
    return redirect('farmer_login')

# Farmer dashboard view
@login_required
def farmer_dashboard(request):
    if not hasattr(request.user, 'farmer'):
        messages.error(request, "No farmer profile found.")
        return redirect('home')

    farmer = request.user.farmer
    products = Produce.objects.filter(farmer=farmer)
    orders = Order.objects.filter(produce__farmer=farmer)

    total_products = products.count()
    total_orders = orders.count()
    total_earnings = sum(
        order.total_price for order in orders if order.status == 'Completed')

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_earnings': total_earnings,
    }
    return render(request, 'farmer_dashboard.html', context)

# Add product view
@login_required
def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        price_per_unit = request.POST['price_per_unit']
        quantity_available = request.POST['quantity_available']
        quality = request.POST['quality']
        description = request.POST['description']
        image = request.FILES.get('image')  # Get uploaded image file

        # Assume the user has a Farmer profile
        farmer = Farmer.objects.get(user=request.user)

        # Create a new product
        Produce.objects.create(
            farmer=farmer,
            name=name,
            price_per_unit=price_per_unit,
            quantity_available=quantity_available,
            quality=quality,
            description=description,
            image=image  # Store the uploaded image
        )

        messages.success(request, "Product added successfully!")
        # Redirect to a list of products or any other page
        return redirect('view_products')

    return render(request, 'add_product.html')

# Edit product view
@login_required
def edit_product(request, product_id):
    product = Produce.objects.get(id=product_id)

    if request.method == 'POST':
        product.name = request.POST['name']
        product.price_per_unit = request.POST['price_per_unit']
        product.quantity_available = request.POST['quantity_available']
        product.quality = request.POST['quality']
        product.description = request.POST['description']

        # If a new image is uploaded, update the image field
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, "Product updated successfully!")
        # Redirect to a list of products or any other page
        return redirect('view_products')

    context = {'product': product}
    return render(request, 'edit_product.html', context)

# Delete product view
@login_required
def delete_product(request, product_id):
    product = get_object_or_404(
        Produce, id=product_id, farmer__user=request.user)

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('view_products')

    context = {'product': product}
    return render(request, 'delete_product.html', context)

# View farmer's orders
@login_required
def view_orders(request):
    farmer = Farmer.objects.get(user=request.user)
    orders = Order.objects.filter(produce__farmer=farmer)

    context = {
        'orders': orders,
    }
    return render(request, 'view_orders.html', context)


@login_required
def view_products(request):
    # Get the farmer linked to the current user
    farmer = Farmer.objects.get(user=request.user)
    # Get the products added by the farmer
    products = Produce.objects.filter(farmer=farmer)

    context = {
        'products': products,
    }
    return render(request, 'view_products.html', context)


@login_required
def ProductCatalogView(request):
    # Retrieve query parameters
    query = request.GET.get('query', '')
    quality = request.GET.get('category', '')  # Change 'category' to 'quality'

    # Filter products by query if it exists
    products = Produce.objects.all()
    if query:
        products = products.filter(name__icontains=query)

    # Filter products by quality if it exists
    if quality:
        products = products.filter(quality=quality)

    return render(request, 'catalog.html', {'products': products, 'categories': Produce.QUALITY_CHOICES})



@login_required
def payment_success(request):
    session_ref = request.GET.get('session_ref')
    if not session_ref:
        return HttpResponse("Missing session reference.", status=400)

    # Retrieve the session or cart using the session_ref
    # This example uses Django's session framework; adapt as needed for your storage method
    order_ref = request.session.get('order_ref')
    if session_ref != order_ref:
        return HttpResponse("Invalid session reference.", status=400)

    cart = request.session.get('cart', {})
    if not cart:
        return HttpResponse("Cart is empty or session has expired.", status=400)

    # Assuming you have cart information to create an order...
    for item_id, quantity in cart.items():
        product = Produce.objects.get(id=item_id)
        Order.objects.create(
            product=product,
            buyer=request.user,
            date_purchased=timezone.now()
        )

    # Optionally, clear the cart from the session
    del request.session['cart']
    del request.session['order_ref']
    request.session.modified = True

    # Redirect to a confirmation page or render a success template
    return render(request, 'payment_success.html')


@login_required
def add_to_cart(request, item_id):
    # Get existing cart or create an empty one
    cart = request.session.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + 1  # Add or increment item quantity
    request.session['cart'] = cart  # Update session cart
    request.session.modified = True  # Mark session as modified

    # Add success message to context
    context = {'success_message': 'Item added to cart successfully!'}

    # Replace with the appropriate template
    return redirect('product_catalog')


def cart(request):
    cart = request.session.get('cart', {})
    items_in_cart = []
    total_cart_price = 0

    if cart:
        for item_id, quantity in cart.items():
            item = Produce.objects.get(pk=item_id)
            total_price = item.price * quantity
            total_cart_price += total_price
            items_in_cart.append({
                'item': item,
                'quantity': quantity,
                'total_price': total_price
            })

    context = {
        'cart': items_in_cart,
        'total_cart_price': total_cart_price
    }
    return render(request, 'cart.html', context)


def update_cart(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action')
    cart = request.session.get('cart', {})

    if item_id and action:
        if action == 'add':
            cart[item_id] = cart.get(item_id, 0) + 1
        elif action == 'remove':
            if item_id in cart:
                cart[item_id] = max(0, cart.get(item_id, 0) - 1)
                if cart[item_id] == 0:
                    del cart[item_id]

    request.session['cart'] = cart
    request.session.modified = True

    return JsonResponse({'success': True})


@login_required
def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(cart.values())  # Total number of items in the cart
    return JsonResponse({'count': count})


def calculate_total_cart_price(cart):
    total_price = 0
    for item_id, quantity in cart.items():
        item = Produce.objects.get(id=item_id)
        total_price += item.price * quantity
    return total_price


# Your Stripe secret key (ensure this is kept secure)
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def create_checkout_session(request):
    # Ensure we have a cart in the session
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'Your cart is empty'}, status=400)

    # Prepare Stripe line items
    line_items = []
    for item_id, quantity in cart.items():
        product = Produce.objects.get(id=item_id)
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': product.name,
                },
                # Stripe expects the amount in cents
                'unit_amount': int(product.price * 100),
            },
            'quantity': quantity,
        }
        line_items.append(line_item)

    # Generate a unique reference for this checkout session
    order_ref = uuid.uuid4()
    request.session['order_ref'] = str(order_ref)

    # Create the Stripe Checkout Session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            billing_address_collection='required',
            success_url=request.build_absolute_uri(
                reverse('payment_success')) + f"?session_ref={order_ref}",
            cancel_url=request.build_absolute_uri(reverse('cancel')),
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Store the Checkout Session ID in the session for potential future use
    request.session['checkout_session_id'] = checkout_session.id

    # Return the session URL to the frontend to redirect the user to Stripe Checkout
    # return JsonResponse({'session_url': checkout_session.url})

    return redirect(checkout_session.url)
    # return JsonResponse({'session_url': checkout_session.url})


def payment_cancel(request):
    # You can add any context or logic here
    return render(request, 'payment_cancel.html')


def ProductDetailsView(request, product_id):
    product = get_object_or_404(Produce, pk=product_id)
    context = {
        'product': product,
    }
    return render(request, 'product_details.html', context)


@login_required
def products_detail_view(request):
    products = Produce.objects.filter(owner=request.user)
    return render(request, 'products_detail.html', {'products': products})


@login_required
def orders_detail_view(request):
    # Ensure the user is a consumer
    if hasattr(request.user, 'consumer'):
        consumer = request.user.consumer
        orders = Order.objects.filter(consumer=consumer)
        return render(request, 'orders_detail.html', {'orders': orders})
    else:
        # Redirect or show an error if the user is not a consumer
        messages.error(request, "You do not have access to order details.")
        return redirect('home')


@login_required
def order_detail_view(request, order_id):
    # Try to get the order object for the logged-in consumer
    try:
        order = get_object_or_404(Order, id=order_id, consumer=request.user.consumer)
    except Consumer.DoesNotExist:
        # If the user is not a consumer, check if they are a delivery person assigned to the order
        if hasattr(request.user, 'deliveryperson'):
            delivery_person = request.user.deliveryperson
            order = get_object_or_404(Order, id=order_id, delivery_person=delivery_person)
        else:
            # If the user is neither a consumer nor a relevant delivery person, restrict access
            messages.error(request, "You do not have access to this order.")
            return redirect('home')

    # Debug: Check if the delivery person is assigned
    if order.delivery_person:
        print(f"Delivery person assigned: {order.delivery_person.user.username}")
    else:
        print("No delivery person assigned to this order.")

    return render(request, 'order_detail.html', {'order': order})

@login_required
def order_detail_view(request, order_id):
    # Try to get the order object for the logged-in consumer
    try:
        order = get_object_or_404(Order, id=order_id, consumer=request.user.consumer)
    except Consumer.DoesNotExist:
        # If the user is not a consumer, check if they are a delivery person assigned to the order
        if hasattr(request.user, 'deliveryperson'):
            delivery_person = request.user.deliveryperson
            order = get_object_or_404(Order, id=order_id, delivery_person=delivery_person)
        else:
            # If the user is neither a consumer nor a relevant delivery person, restrict access
            messages.error(request, "You do not have access to this order.")
            return redirect('home')

    # Debug: Check if the delivery person is assigned
    if order.delivery_person:
        print(f"Delivery person assigned: {order.delivery_person.user.username}")
    else:
        print("No delivery person assigned to this order.")

    return render(request, 'order_detail.html', {'order': order})


@login_required
def payment_success(request):
    session_ref = request.GET.get('session_ref')
    if not session_ref:
        return HttpResponse("Missing session reference.", status=400)

    # Validate the session reference
    order_ref = request.session.get('order_ref')
    if session_ref != order_ref:
        return HttpResponse("Invalid session reference.", status=400)

    cart = request.session.get('cart', {})
    if not cart:
        return HttpResponse("Cart is empty or session has expired.", status=400)

    # Retrieve the Consumer instance associated with the user
    try:
        consumer = request.user.consumer
    except Consumer.DoesNotExist:
        return HttpResponse("Consumer profile not found.", status=400)

    # Retrieve delivery options from session
    delivery_or_pickup = request.session.get('delivery_or_pickup')
    delivery_address = request.session.get('delivery_address', "")

    # Process each item in the cart to create an order
    for item_id, quantity in cart.items():
        product = Produce.objects.get(id=item_id)
        Order.objects.create(
            produce=product,
            consumer=consumer,
            quantity_ordered=quantity,
            total_price=product.price_per_unit * quantity,
            delivery_or_pickup=delivery_or_pickup,
            delivery_address=delivery_address
        )

    # Clear cart and order reference from session
    del request.session['cart']
    del request.session['order_ref']
    del request.session['delivery_or_pickup']
    del request.session['delivery_address']
    request.session.modified = True

    # Redirect to a confirmation page or render a success template
    return render(request, 'payment_success.html')


def payment_cancel(request):
    # You can add any context or logic here
    return render(request, 'payment_cancel.html')

@login_required
def add_to_cart(request, item_id):
    # Get existing cart or create an empty one
    cart = request.session.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + 1  # Add or increment item quantity
    request.session['cart'] = cart  # Update session cart
    request.session.modified = True  # Mark session as modified

    # Add success message to context
    context = {'success_message': 'Item added to cart successfully!'}

    # Replace with the appropriate template
    return redirect('product_catalog')


def cart(request):
    cart = request.session.get('cart', {})
    items_in_cart = []
    total_cart_price = 0

    if cart:
        for item_id, quantity in cart.items():
            item = Produce.objects.get(pk=item_id)
            total_price = item.price_per_unit * quantity
            total_cart_price += total_price
            items_in_cart.append({
                'item': item,
                'quantity': quantity,
                'total_price': total_price
            })

    context = {
        'cart': items_in_cart,
        'total_cart_price': total_cart_price
    }
    return render(request, 'cart.html', context)


def update_cart(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action')
    cart = request.session.get('cart', {})

    if item_id and action:
        if action == 'add':
            cart[item_id] = cart.get(item_id, 0) + 1
        elif action == 'remove':
            if item_id in cart:
                cart[item_id] = max(0, cart.get(item_id, 0) - 1)
                if cart[item_id] == 0:
                    del cart[item_id]

    request.session['cart'] = cart
    request.session.modified = True

    return JsonResponse({'success': True})


@login_required
def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(cart.values())  # Total number of items in the cart
    return JsonResponse({'count': count})


def calculate_total_cart_price(cart):
    total_price = 0
    for item_id, quantity in cart.items():
        item = Produce.objects.get(id=item_id)
        total_price += item.price * quantity
    return total_price


# Your Stripe secret key (ensure this is kept secure)
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def create_checkout_session(request):
    # Ensure we have a cart in the session
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'Your cart is empty'}, status=400)

    # Capture additional details from request if provided
    delivery_or_pickup = request.POST.get('delivery_or_pickup')
    delivery_address = request.POST.get(
        'delivery_address') if delivery_or_pickup == 'Delivery' else ""

    # Save delivery options in session for later use in payment success
    request.session['delivery_or_pickup'] = delivery_or_pickup
    request.session['delivery_address'] = delivery_address

    # Prepare Stripe line items
    line_items = []
    for item_id, quantity in cart.items():
        product = Produce.objects.get(id=item_id)
        line_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': product.name,
                },
                # Stripe expects amount in cents
                'unit_amount': int(product.price_per_unit * 100),
            },
            'quantity': quantity,
        }
        line_items.append(line_item)

    # Generate a unique reference for this checkout session
    order_ref = uuid.uuid4()
    request.session['order_ref'] = str(order_ref)

    # Create the Stripe Checkout Session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(
                reverse('payment_success')) + f"?session_ref={order_ref}",
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Store the Checkout Session ID in the session for potential future use
    request.session['checkout_session_id'] = checkout_session.id

    # Return the session URL to the frontend to redirect the user to Stripe Checkout
    return redirect(checkout_session.url)

# Delivery person registration view
def delivery_person_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        contact_number = request.POST['contact_number']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('delivery_person_signup')

        user = User.objects.create_user(username=username, password=password)
        delivery_person = DeliveryPerson(
            user=user, contact_number=contact_number)
        delivery_person.save()

        messages.success(request, "Delivery person registered successfully!")
        return redirect('delivery_person_login')

    return render(request, 'delivery_person_signup.html')

# Delivery person login view
def delivery_person_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and hasattr(user, 'deliveryperson'):
            login(request, user)
            return redirect('delivery_dashboard')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('delivery_person_login')

    return render(request, 'delivery_person_login.html')


@login_required
def delivery_dashboard(request):
    if not hasattr(request.user, 'deliveryperson'):
        messages.error(request, "No delivery person profile found.")
        return redirect('home')

    delivery_person = request.user.deliveryperson
    # Get only the orders assigned to this delivery person
    assigned_orders = Order.objects.filter(
        delivery_person=delivery_person, status__in=['Pending', 'In Transit'])

    return render(request, 'delivery_dashboard.html', {'assigned_orders': assigned_orders})



# Chat view for delivery person and consumer
@login_required
def chat_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Handle POST request for sending a new message
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        message_content = request.POST.get('message')

        if not message_content:
            return JsonResponse({'success': False, 'error': 'Message content is empty'})

        new_message = Message.objects.create(
            order=order,
            sender=request.user,
            content=message_content,
            timestamp=timezone.now()
        )
        return JsonResponse({
            'success': True,
            'message': {
                'id': new_message.id,
                'sender': new_message.sender.username,
                'content': new_message.content,
                'timestamp': new_message.timestamp.strftime("%H:%M %p")
            }
        })

    # Handle AJAX GET request for fetching new messages
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        last_message_id = request.GET.get('last_message_id')
        if last_message_id:
            new_messages = order.messages.filter(
                id__gt=last_message_id).order_by('timestamp')
        else:
            new_messages = order.messages.order_by('timestamp')

        messages_data = [
            {
                'id': message.id,
                'sender': message.sender.username,
                'content': message.content,
                'timestamp': message.timestamp.strftime("%H:%M %p")
            } for message in new_messages
        ]
        return JsonResponse({'messages': messages_data})

    # Initial GET request (non-AJAX) to load the chat page
    messages = order.messages.order_by('timestamp')
    return render(request, 'chat.html', {'order': order, 'messages': messages})

# Mark order as delivered
@login_required
def mark_order_delivered(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.user.deliveryperson == order.delivery_person:
        order.status = 'Delivered'
        order.save()
        messages.success(request, "Order marked as delivered.")
    else:
        messages.error(request, "Unauthorized action.")
    return redirect('delivery_dashboard')


@login_required
def delivery_view_orders(request):
    # Check if the user is a delivery person
    if hasattr(request.user, 'deliveryperson'):
        delivery_person = request.user.deliveryperson

        # Get only the orders assigned to this delivery person
        assigned_orders = Order.objects.filter(delivery_person=delivery_person)

        context = {
            'assigned_orders': assigned_orders,
        }
        return render(request, 'delivery_view_orders.html', context)

    else:
        messages.error(
            request, "You do not have permission to view assigned orders.")
        # Redirect to home or an appropriate page
        return redirect('delivery_dashboard')

# Farmer logout view
def delivery_person_logout(request):
    logout(request)
    return redirect('delivery_person_login')


@login_required
def assign_delivery_person(request, order_id, delivery_person_id):
    # Retrieve the order and delivery person objects
    order = get_object_or_404(Order, id=order_id)
    delivery_person = get_object_or_404(DeliveryPerson, id=delivery_person_id)

    # Assign the delivery person to the order
    order.delivery_person = delivery_person
    order.status = 'In Transit'  # Optionally update the status

    # Save the order to persist changes to the database
    order.save()

    # Optional: Also add this order to the delivery person's assigned orders
    delivery_person.assigned_orders.add(order)

    messages.success(request, "Delivery person assigned successfully!")
    return redirect('view_orders')
