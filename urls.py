from django.urls import path
from . import views

urlpatterns = [
    # --------------------------------------------------------
    # Public pages & core navigation
    # --------------------------------------------------------

    # Landing page: hero + featured deals + popular items + reviews
    path("", views.home_view, name="home"),

    # Static-ish pages managed from the database
    path("about/", views.about_view, name="about"),     # About BurgerInn (admin-editable)
    path("deals/", views.deals_view, name="deals"),     # List of active deals
    path("reviews/", views.reviews_view, name="reviews"),  # Review form + list of reviews

    # Full menu: filters, veg/spicy toggles, favourites heart, etc.
    path("menu/", views.menu_view, name="menu"),

    # --------------------------------------------------------
    # Authentication & profile
    # --------------------------------------------------------

    # Login: styled page using Django AuthenticationForm
    path("login/", views.login_view, name="login"),

    # Signup: uses custom SignUpForm (captures email, phone, address)
    path("signup/", views.signup_view, name="signup"),

    # Logout: ends session and redirects to home
    path("logout/", views.logout_view, name="logout"),

    # Profile page: shows user profile, favourites, and order history
    path("profile/", views.profile_view, name="profile"),

    # --------------------------------------------------------
    # Cart & checkout flow
    # --------------------------------------------------------

    # Cart page: renders items stored in session cart
    path("cart/", views.cart_view, name="cart"),

    # Add item to cart (POST) – supports optional size/qty
    path("cart/add/<int:item_id>/", views.cart_add, name="cart_add"),

    # Update quantity of a line in the cart (POST)
    path("cart/update/<int:item_id>/", views.cart_update, name="cart_update"),

    # Remove a single line from the cart (POST)
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),

    # Clear entire cart (POST)
    path("cart/clear/", views.cart_clear, name="cart_clear"),

    # Checkout page:
    # - captures full name, contact, order_type, address/store_location
    # - applies optional deal code with DealRequirement logic
    # - creates Order + OrderItem rows
    path("checkout/", views.checkout_view, name="checkout"),

    # --------------------------------------------------------
    # Favourites
    # --------------------------------------------------------

    # Favourites list: shows all MenuItems the user has liked
    path("favorites/", views.favorites_view, name="favorites"),

    # Toggle favourite ♥ for a given MenuItem (POST)
    path(
        "favorites/toggle/<int:item_id>/",
        views.favorite_toggle,
        name="favorite_toggle",
    ),

    # --------------------------------------------------------
    # Order tracker
    # --------------------------------------------------------

    # “My Orders” tracker:
    # - shows latest active order (pending / in_oven / on_the_way / completed)
    # - drives progress bar UI
    path("orders/", views.orders_view, name="orders"),

    # When user clicks “Order ready – Back to home”
    # marks order as acknowledged so it no longer appears in tracker
    path(
        "orders/ack/<int:order_id>/",
        views.order_acknowledge_view,
        name="order_acknowledge",
    ),
]
