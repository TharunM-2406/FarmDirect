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


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        # password2 = request.POST['password2']

        if len(username) < 6:
            messages.error(
                request, "Username must be at least 6 characters long")
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
        user.save()
        return redirect('home')

    return render(request, 'register.html')


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
            # Create the user
            user = User.objects.create_user(
                username=username, password=password)

            # Decode the base64 face image
            if face_image_data:
                format, imgstr = face_image_data.split(';base64,')
                ext = format.split('/')[-1]
                face_image = ContentFile(base64.b64decode(
                    imgstr), name=f'{username}_face.{ext}')

                # Process the face image with face_recognition to get face encoding
                # Assuming face_recognition is used for face processing.
                # You would save the encoding or image in the Farmer model.

                # Load the image into a numpy array
                img_array = face_recognition.load_image_file(face_image)

                # Detect face encodings from the image
                face_encodings = face_recognition.face_encodings(img_array)

                if len(face_encodings) > 0:
                    # Assuming one face is present
                    face_encoding = face_encodings[0]
                    # You can convert this encoding to a list and save it as a JSON string in the database
                    face_encoding_json = face_encoding.tolist()
                else:
                    messages.error(
                        request, "No face detected, please try again.")
                    return redirect('farmer_signup')

            else:
                messages.error(
                    request, "No face image provided, please capture your face.")
                return redirect('farmer_signup')

            # Save the farmer record
            farmer = Farmer(
                user=user,
                farm_name=farm_name,
                location=location,
                contact_number=contact_number,
                face_encoding=face_encoding_json  # Store the face encoding JSON
            )
            farmer.save()

            messages.success(request, "Farmer registered successfully!")
            # Redirect to login or a different page after signup
            return redirect('login')
        except IntegrityError:
            messages.error(request, "Username already taken!")
            return redirect('farmer_signup')

    return render(request, 'farmer_signup.html')

def farmer_login(request):
    if request.method == 'POST':
        if 'face_image' in request.POST:
            # Handle face recognition login
            face_image_data = request.POST.get('face_image')

            # Decode the base64 image and remove the 'data:image/png;base64,' prefix
            face_image_data = face_image_data.split(',')[1]
            face_image_bytes = base64.b64decode(face_image_data)
            image = Image.open(BytesIO(face_image_bytes))

            # Ensure image is in RGB format
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert the image into a NumPy array and extract face encoding
            image_array = np.array(image)
            face_encodings_list = face_encodings(image_array)

            if len(face_encodings_list) == 0:
                # No face detected in the image
                return JsonResponse({'success': False, 'message': 'No face detected. Please try again.'})

            # Use the first detected face encoding
            face_encoding = face_encodings_list[0]

            # Iterate through stored farmer face encodings and check for a match
            farmers = Farmer.objects.exclude(face_encoding__isnull=True)
            for farmer in farmers:
                if farmer.face_encoding:
                    # Load the stored face encoding
                    stored_encoding = json.loads(farmer.face_encoding)
                    stored_encoding = np.array(stored_encoding)

                    if stored_encoding is not None and len(stored_encoding) > 0:
                        # Use face_recognition's compare_faces method to match
                        match = compare_faces([stored_encoding], face_encoding)
                        if match[0]:  # If a match is found
                            login(request, farmer.user)
                            return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})

            return JsonResponse({'success': False, 'message': 'Face ID not found'})

        # Traditional username/password login
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('farmer_dashboard')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('farmer_login')

    return render(request, 'farmer_login.html')

# Farmer logout view
def farmer_logout(request):
    logout(request)
    return redirect('farmer_login')

# Farmer dashboard view
@login_required
def farmer_dashboard(request):
    # Assuming user is linked to Farmer
    farmer = Farmer.objects.get(user=request.user)
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
    farmer = Farmer.objects.get(user=request.user)

    if request.method == 'POST':
        name = request.POST['name']
        price_per_unit = request.POST['price_per_unit']
        quantity_available = request.POST['quantity_available']
        quality = request.POST['quality']
        description = request.POST['description']

        Produce.objects.create(
            farmer=farmer,
            name=name,
            price_per_unit=price_per_unit,
            quantity_available=quantity_available,
            quality=quality,
            description=description
        )
        messages.success(request, 'Product added successfully!')
        return redirect('farmer_dashboard')

    return render(request, 'add_product.html')

# Edit product view
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(
        Produce, id=product_id, farmer__user=request.user)

    if request.method == 'POST':
        product.name = request.POST['name']
        product.price_per_unit = request.POST['price_per_unit']
        product.quantity_available = request.POST['quantity_available']
        product.quality = request.POST['quality']
        product.description = request.POST['description']
        product.save()

        messages.success(request, 'Product updated successfully!')
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
    orders = Order.objects.filter(consumer=request.user)
    return render(request, 'orders_detail.html', {'orders': orders})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, consumer=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def payment_success(request):
    session_ref = request.GET.get('session_ref')
    if not session_ref:
        return HttpResponse("Missing session reference.", status=400)

    # Retrieve the session or cart using the session_ref
    order_ref = request.session.get('order_ref')
    if session_ref != order_ref:
        return HttpResponse("Invalid session reference.", status=400)

    cart = request.session.get('cart', {})
    if not cart:
        return HttpResponse("Cart is empty or session has expired.", status=400)

    # Process each item in the cart to create an order
    for item_id, quantity in cart.items():
        product = Produce.objects.get(id=item_id)
        Order.objects.create(
            produce=product,
            consumer=request.user,
            quantity_ordered=quantity,
            total_price=product.price_per_unit * quantity,
            delivery_or_pickup='Delivery',  # or 'Pickup', depending on your logic
        )

    # Clear the cart from the session
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