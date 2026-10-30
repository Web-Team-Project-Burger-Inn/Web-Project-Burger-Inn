"""
Views for the BurgerInn customer-facing site.

Main features covered here:
- Home page (hero, deals, popular items, reviews)
- Authentication (signup / login / logout)
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Avg, Count
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SignUpForm
from .models import Deal, MenuItem, Review
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

