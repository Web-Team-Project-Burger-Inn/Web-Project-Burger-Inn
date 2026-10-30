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

 
