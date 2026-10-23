"""
Views for the BurgerInn customer-facing site.

Main features covered here:
- Home page (hero, deals, popular items, reviews)
- About page (admin-managed content)
- Deals listing
- User profile (with favourites + past orders)
- Authentication (signup / login / logout)
- Reviews (list + submit)
- Cart + checkout (including deal code logic)
- Menu browsing (filters, sorting, favourites)
- Favourites toggle
- Order tracking + acknowledgement
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Prefetch, Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ReservationForm, ReviewForm, SignUpForm
from .models import (
    About,
    Deal,
    MenuCategory,
    MenuItem,
    MenuItemSize,
    Review,
    UserProfile,
    Favorite,
    Order,
    OrderItem,
)
from .cart import add_item, set_qty, remove_item, clear, build_cart_context


# =====================================================================
# DEAL / DISCOUNT HELPERS
# =====================================================================

def _compute_deal_percentage_discount(deal: Deal, cart_items) -> Decimal:
    """
    FEATURE: Percentage-based deal engine for the checkout.

    Applies `deal.discount_percentage` ONLY to items that match each
    DealRequirement (category + optional size), and only up to the
    required quantity per requirement.

    Example:
        - DealRequirement: category = "Burger", size = "L", min_quantity = 2
        - Cart: 3x Large Burger + 1x Medium Burger
        → Only 2x Large Burger are eligible for the percentage discount.

    If:
        - no requirements exist, or
        - the percentage is not set / <= 0
    this helper returns 0 and the checkout logic can fall back to other
    behaviours.
    """
    if not deal or not deal.discount_percentage:
        return Decimal("0.00")

    # All requirements attached to this deal (category + optional size)
    requirements = list(deal.requirements.select_related("category"))
    if not requirements:
        # No requirements defined → let caller fall back to old behaviour.
        return Decimal("0.00")

    # Convert percentage (e.g. 20) to decimal (0.20) with safe rounding
    pct = (deal.discount_percentage / Decimal("100")).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )

    total_discount = Decimal("0.00")

    # For each requirement (category/size/qty), we scan the cart
    for req in requirements:
        remaining = req.min_quantity or 0
        if remaining <= 0:
            continue

        for row in cart_items:
            if remaining <= 0:
                break

            item = row["item"]
            size = row.get("size")
            qty = row["qty"]
            unit_price = row["price"]

            # Category must match
            if item.category_id != req.category_id:
                continue

            # Optional size restriction
            if req.size and size != req.size:
                continue

            if qty <= 0:
                continue

            # How many units in this line can still count for this requirement?
            eligible_qty = min(remaining, qty)
            if eligible_qty <= 0:
                continue

            line_discount = (unit_price * pct) * eligible_qty
            total_discount += line_discount
            remaining -= eligible_qty

    # Money: round to 2 decimals (Rs xx.xx)
    return total_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =====================================================================
# PUBLIC PAGES
# =====================================================================

# -------------------
# Home page
# -------------------
def home_view(request):
    """
    FEATURE: Landing page.

    Shows:
    - Active deals (limited set)
    - Popular / featured menu items
    - Latest customer reviews
    - Review statistics (average rating + count)
    """
    today = timezone.now().date()

    # Active deals for landing (limited to 3)
    deals = (
        Deal.objects.filter(start_date__lte=today, end_date__gte=today)
        .order_by("start_date")[:3]
    )

    # Popular / featured menu items – same style as on menu page
    popular_items = (
        MenuItem.objects.filter(is_available=True)
        .select_related("category")
        .order_by("category__sort_order", "name")[:6]
    )

    # Latest reviews (most recent first)
    latest_reviews = Review.objects.order_by("-created_at")[:6]

    # Overall rating summary for the "Reviews" section
    review_stats = Review.objects.aggregate(
        avg_rating=Avg("rating"),
        total_reviews=Count("id"),
    )

    return render(
        request,
        "pages/home.html",
        {
            "deals": deals,
            # exposed under both names so template variants stay compatible
            "featured_items": popular_items,
            "popular_items": popular_items,
            "reviews": latest_reviews,
            "review_stats": review_stats,
        },
    )


# -------------------
# About page
# -------------------
def about_view(request):
    """
    FEATURE: About page.

    Content is managed from the Django admin using the About model.
    We always show the most recently updated About entry.
    """
    about = About.objects.order_by("-last_updated").first()
    social_links = (
        about.social_links if about and getattr(about, "social_links", None) else {}
    )
    return render(
        request,
        "pages/about.html",
        {
            "about": about,
            "social_links": social_links,
        },
    )


# -------------------
# Deals page
# -------------------
def deals_view(request):
    """
    FEATURE: Deals listing page.

    Shows all deals that are currently active based on date range.
    """
    today = date.today()
    active_deals = Deal.objects.filter(start_date__lte=today, end_date__gte=today)
    return render(request, "pages/deals.html", {"deals": active_deals})


# =====================================================================
# PROFILE
# =====================================================================

@login_required(login_url="login")
def profile_view(request):
    """
    FEATURE: User profile page.

    Shows:
    - Basic profile info (from UserProfile)
    - Favourites list
    - Past orders (most recent first)
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related("item", "item__category")

    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__item")
        .order_by("-created_at")
    )

    return render(
        request,
        "pages/profile.html",
        {
            "profile": profile,
            "favorites": favorites,
            "orders": orders,
        },
    )


# =====================================================================
# AUTHENTICATION
# =====================================================================

def signup_view(request):
    """
    FEATURE: User signup.

    Uses custom SignUpForm so we can capture extra fields
    (e.g. phone, address) and optionally populate UserProfile.
    """
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # SignUpForm is responsible for creating user + profile
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("home")
        messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()

    return render(request, "pages/signup.html", {"form": form})


def login_view(request):
    """
    FEATURE: User login.

    Uses Django's built-in AuthenticationForm and respects ?next=...
    so users are redirected back to the page that required login.
    """
    next_url = request.GET.get("next") or request.POST.get("next") or None

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(next_url or "home")
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm(request)

    return render(request, "pages/login.html", {"form": form, "next": next_url})


def logout_view(request):
    """
    FEATURE: Logout.

    Clears the session and redirects back to home.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# =====================================================================
# REVIEWS
# =====================================================================

def reviews_view(request):
    """
    FEATURE: Reviews page.

    - GET: list all reviews
    - POST: create a new review (only for logged-in users)
    """
    reviews = Review.objects.all()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to submit a review.")
            return redirect(f"{reverse('login')}?next={reverse('reviews')}")

        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for your review! 🍕")
            return redirect("reviews")
        messages.error(request, "Please fix the errors below.")
    else:
        form = ReviewForm()

    return render(
        request,
        "pages/reviews.html",
        {
            "form": form,
            "reviews": reviews,
        },
    )


# =====================================================================
# CHECKOUT + DEAL CODE / ORDER CREATION
# =====================================================================

@login_required(login_url="login")
def checkout_view(request):
    """
    FEATURE: Checkout flow.

    Responsibilities:
    - Validate that the cart is not empty
    - Handle the reservation/checkout form (customer details, deal code, etc.)
    - Validate and apply deal codes (date range, minimum subtotal, requirements)
    - Create the Order and OrderItem rows
    - Clear the cart and display a success page
    """
    cart_ctx = build_cart_context(request)

    # If nothing in cart, redirect them back to menu
    if cart_ctx["cart_total_qty"] == 0:
        messages.error(request, "Your cart is empty. Add something to your cart first.")
        return redirect("menu")

    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            subtotal = cart_ctx["cart_subtotal"]
            delivery_fee = Decimal("0.00")  # currently no delivery fee

            # -------------------------------------------
            # DEAL CODE LOGIC
            # -------------------------------------------
            deal_code = (cd.get("deal_code") or "").strip().upper()
            applied_deal = None
            discount_amount = Decimal("0.00")

            if deal_code:
                today = timezone.now().date()

                # Fetch an active deal matching this code
                applied_deal = (
                    Deal.objects.filter(
                        code__iexact=deal_code,
                        start_date__lte=today,
                        end_date__gte=today,
                    )
                    .prefetch_related("requirements__category")
                    .first()
                )

                if not applied_deal:
                    messages.error(
                        request,
                        "This deal code is not valid or has expired.",
                    )
                    return render(
                        request,
                        "pages/checkout.html",
                        {"form": form, **cart_ctx},
                    )

                # (1) Minimum subtotal requirement, using original_price as the threshold
                if (
                    applied_deal.original_price
                    and subtotal < applied_deal.original_price
                ):
                    messages.error(
                        request,
                        (
                            "This deal requires a minimum items total of "
                            f"Rs {applied_deal.original_price}."
                        ),
                    )
                    return render(
                        request,
                        "pages/checkout.html",
                        {"form": form, **cart_ctx},
                    )

                # (2) Category (+size) based requirements – ensure cart meets all
                requirements = list(applied_deal.requirements.all())
                if requirements:
                    for req in requirements:
                        have_qty = 0

                        # Iterate directly over list produced by build_cart_context
                        for row in cart_ctx["cart_items"]:
                            item = row["item"]
                            size = row.get("size")

                            if item.category_id != req.category_id:
                                continue
                            if req.size and size != req.size:
                                continue

                            have_qty += row["qty"]

                        if have_qty < req.min_quantity:
                            msg_bits = [f"at least {req.min_quantity} item(s) from"]
                            if req.size:
                                msg_bits.append(f"size {req.get_size_display()} of")
                            msg_bits.append(f"category '{req.category.name}'.")
                            messages.error(
                                request,
                                "This deal requires " + " ".join(msg_bits),
                            )
                            return render(
                                request,
                                "pages/checkout.html",
                                {"form": form, **cart_ctx},
                            )

                # (3) Compute discount:
                #     - if requirements exist → apply % only on matching items
                #     - else → fall back to a simple fixed discount amount
                if requirements:
                    discount_amount = _compute_deal_percentage_discount(
                        applied_deal,
                        cart_ctx["cart_items"],
                    )
                else:
                    # Legacy behaviour for deals with no requirements
                    discount_amount = applied_deal.discount_amount

            # Final total with discount + delivery
            total = subtotal + delivery_fee - discount_amount
            if total < 0:
                total = Decimal("0.00")

            # Create the main Order record
            order = Order.objects.create(
                user=request.user,
                full_name=cd["full_name"],
                phone=cd["phone"],
                email=cd["email"],
                order_type=cd["order_type"],
                address=cd.get("address") or "",
                store_location=cd.get("store_location") or "",
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
                deal=applied_deal if deal_code else None,
                deal_code=deal_code if deal_code else "",
                deal_discount_amount=discount_amount,
            )

            # Order items: one row per item in the cart
            for row in cart_ctx["cart_items"]:
                OrderItem.objects.create(
                    order=order,
                    item=row["item"],
                    size=row["size"],
                    size_label=row["size_label"],
                    quantity=row["qty"],
                    unit_price=row["price"],
                    line_total=row["line_total"],
                )

            # Clear cart after successful order
            clear(request)

            # Friendly success message depending on deal usage
            if deal_code and discount_amount > 0:
                messages.success(
                    request,
                    f"Your order has been placed! Deal {deal_code} applied! 🍕",
                )
            else:
                messages.success(request, "Your order has been placed! 🍕")

            return render(request, "pages/order_success.html", {"order": order})

    else:
        # Pre-fill email field when user has one
        initial = {"email": request.user.email} if request.user.email else {}
        form = ReservationForm(initial=initial)

    return render(request, "pages/checkout.html", {"form": form, **cart_ctx})


# =====================================================================
# MENU
# =====================================================================

def menu_view(request):
    """
    FEATURE: Menu page.

    Supports:
    - Free-text search by name / description (?q=)
    - Category filter (?cat=)
    - Veg-only filter (?veg=1)
    - Spicy-only filter (?spicy=1)
    - Sorting by name / price (asc/desc)
    - Favourites highlighting for logged-in users
    """
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("cat", "").strip()
    only_veg = request.GET.get("veg") == "1"
    only_spicy = request.GET.get("spicy") == "1"
    sort = request.GET.get("sort", "name")

    items = MenuItem.objects.filter(is_available=True).select_related("category")

    # Text search
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q))

    # Category filter
    if cat:
        items = items.filter(category__slug=cat)

    # Veg-only filter
    if only_veg:
        items = items.filter(is_veg=True)

    # Spicy-only filter
    if only_spicy:
        items = items.filter(is_spicy=True)

    # Sorting
    if sort == "price_asc":
        items = items.order_by("price", "name")
    elif sort == "price_desc":
        items = items.order_by("-price", "name")
    else:
        items = items.order_by("name")

    # Mark favourites for the current user
    fav_ids = (
        set(Favorite.objects.filter(user=request.user).values_list("item_id", flat=True))
        if request.user.is_authenticated
        else set()
    )

    for item in items:
        # used in templates to render "favourite" heart state
        item.is_favorite = item.id in fav_ids

    # Categories sidebar / tabs
    categories = MenuCategory.objects.filter(is_active=True).order_by(
        "sort_order",
        "name",
    )
    categories = categories.prefetch_related(
        Prefetch(
            "items",
            queryset=MenuItem.objects.filter(is_available=True).only("id"),
        )
    )

    return render(
        request,
        "pages/menu.html",
        {
            "categories": categories,
            "items": items,
            "active_cat": cat,
            "q": q,
            "only_veg": only_veg,
            "only_spicy": only_spicy,
            "sort": sort,
        },
    )


# =====================================================================
# CART
# =====================================================================

@login_required(login_url="login")
def cart_view(request):
    """
    FEATURE: Cart detail page.

    Uses the shared `build_cart_context` helper from cart.py to compute:
    - line totals
    - subtotal
    - total quantity
    """
    return render(request, "pages/cart.html", build_cart_context(request))


@login_required(login_url="login")
@require_POST
def cart_add(request, item_id):
    """
    FEATURE: Add item to cart.

    Validates size (when provided), then delegates to `add_item` in cart.py.
    """
    item = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    size = request.POST.get("size") or None

    # Validate that the chosen size is available for this item
    if size and not MenuItemSize.objects.filter(item=item, size=size).exists():
        messages.error(request, "Selected size is not available.")
        return redirect(request.POST.get("next") or reverse("menu"))

    qty = max(1, int(request.POST.get("qty", 1)))
    add_item(request, item_id=item.id, size=size, qty=qty)

    disp_size = dict(MenuItemSize.SIZE_CHOICES).get(size, "") if size else ""
    suffix = f" ({disp_size})" if disp_size else ""

    messages.success(request, f"Added {item.name}{suffix} ×{qty} to your cart.")
    return redirect(request.POST.get("next") or reverse("menu"))


@login_required(login_url="login")
@require_POST
def cart_update(request, item_id):
    """
    FEATURE: Update quantity of a single line in the cart.
    """
    item = get_object_or_404(MenuItem, pk=item_id)
    size = request.POST.get("size") or None
    qty = int(request.POST.get("qty", 1))

    set_qty(request, item_id=item.id, size=size, qty=qty)

    disp_size = dict(MenuItemSize.SIZE_CHOICES).get(size, "") if size else ""
    suffix = f" ({disp_size})" if disp_size else ""

    messages.info(request, f"Updated {item.name}{suffix} to quantity {qty}.")
    return redirect("cart")


@login_required(login_url="login")
@require_POST
def cart_remove(request, item_id):
    """
    FEATURE: Remove a line (item + optional size) from the cart.
    """
    item = get_object_or_404(MenuItem, pk=item_id)
    size = request.POST.get("size") or None

    remove_item(request, item_id=item.id, size=size)

    disp_size = dict(MenuItemSize.SIZE_CHOICES).get(size, "") if size else ""
    suffix = f" ({disp_size})" if disp_size else ""

    messages.warning(request, f"Removed {item.name}{suffix} from your cart.")
    return redirect("cart")


@login_required(login_url="login")
@require_POST
def cart_clear(request):
    """
    FEATURE: Clear the entire cart.
    """
    clear(request)
    messages.info(request, "Your cart is now empty.")
    return redirect("cart")


# =====================================================================
# FAVORITES
# =====================================================================

@login_required(login_url="login")
def favorites_view(request):
    """
    FEATURE: Favourites page.

    Shows all favourite items for the current user.
    """
    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related("item", "item__category")
    return render(request, "pages/favorites.html", {"favorites": favorites})


@login_required(login_url="login")
@require_POST
def favorite_toggle(request, item_id):
    """
    FEATURE: Toggle favourite for a specific menu item.

    - If the item is not yet a favourite → create Favorite
    - If it is already favourited       → remove Favorite

    Redirects back to:
      - `next` (hidden input) if present, otherwise
      - HTTP_REFERER, otherwise
      - menu page.
    """
    item = get_object_or_404(MenuItem, pk=item_id, is_available=True)

    fav, created = Favorite.objects.get_or_create(user=request.user, item=item)

    if created:
        messages.success(request, f"Added {item.name} to your favourites.")
    else:
        fav.delete()
        messages.info(request, f"Removed {item.name} from your favourites.")

    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("menu")
    )
    return redirect(next_url)


# =====================================================================
# ORDER TRACKING
# =====================================================================

@login_required(login_url="login")
def orders_view(request):
    """
    FEATURE: My Order / Order Tracker page.

    Shows the latest *active* order for the logged-in user, excluding:
    - cancelled
    - already acknowledged orders (we mark those with "[ACK]" in notes)

    The template uses `progress_step` to visualize where the order is:
        1 = pending
        2 = in oven
        3 = on the way
        4 = completed
    """

    current_order = (
        Order.objects.filter(user=request.user)
        .exclude(status="cancelled")
        .exclude(notes__icontains="[ACK]")  # hide acknowledged orders
        .prefetch_related("items__item", "items__item__category")
        .order_by("-created_at")
        .first()
    )

    progress_step = 0
    if current_order:
        status_to_step = {
            "pending": 1,
            "in_oven": 2,
            "on_the_way": 3,
            "completed": 4,
        }
        progress_step = status_to_step.get(current_order.status, 1)

    return render(
        request,
        "pages/orders.html",
        {
            "current_order": current_order,
            "progress_step": progress_step,
        },
    )


@login_required(login_url="login")
def order_acknowledge_view(request, order_id):
    """
    FEATURE: Acknowledge completed order.

    Called when user clicks 'Order ready – Back to home'.
    We:
    - append "[ACK]" marker to `notes` on the order
    - use that marker to hide the order from the tracker
    - redirect back to home.
    """
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status == "completed":
        marker = "[ACK]"
        notes = order.notes or ""
        if marker not in notes:
            order.notes = (notes + "\n" + marker).strip()
            order.save(update_fields=["notes"])

    messages.success(request, "Enjoy your burger! 🍔")
    return redirect("home")
