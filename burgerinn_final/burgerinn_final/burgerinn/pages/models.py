from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

User = get_user_model()


# ============================================================
#                       DEALS
# ============================================================

class Deal(models.Model):
    """
    FEATURE: Marketing deal / promotion.

    - Shown on Deals page and home page.
    - Can optionally have a `code` (e.g. MARGH500) which is typed
      at checkout to apply a discount.
    - Supports:
        * original_price  → “normal” total
        * price           → discounted total
        * discount_percentage → auto-computed in save()
      plus a date range (start_date / end_date).
    """

    DEAL_TYPES = [
        ("Combo", "Combo"),
        ("Student Special", "Student Special"),
        ("Happy Hour", "Happy Hour"),
        ("Family Feast", "Family Feast"),
        ("Weekday Saver", "Weekday Saver"),
        ("Weekend Special", "Weekend Special"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()

    # Code user will type at checkout, e.g. “MARGH500”
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Optional promo code the customer can enter at checkout, e.g. MARGH500.",
    )

    # Pricing for display + discount logic
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    original_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Computed from original_price and price.",
    )

    # Validity window
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=timezone.now)

    deal_type = models.CharField(
        max_length=50,
        choices=DEAL_TYPES,
        default="Combo",
    )

    terms_conditions = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="deals/", blank=True, null=True)

    def save(self, *args, **kwargs):
        """
        Auto-calculate discount_percentage from original_price and price
        whenever both are set.
        """
        if self.original_price and self.price:
            self.discount_percentage = round(
                (self.original_price - self.price) / self.original_price * 100, 2
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    @property
    def discount_amount(self) -> Decimal:
        """
        How much money the deal saves vs original_price.
        Used in the checkout logic when no per-category rules are present.
        """
        try:
            return self.original_price - self.price
        except TypeError:
            return Decimal("0.00")


# ============================================================
#                       ABOUT PAGE CONTENT
# ============================================================

class About(models.Model):
    """
    FEATURE: Editable "About us" content.

    Admin can edit:
    - title + description (story text)
    - founded_year, founder_name
    - address + contact info
    - social_links (JSON) for dynamic icons/links on the page.
    """

    title = models.CharField(max_length=255)
    description = models.TextField()
    founded_year = models.PositiveSmallIntegerField(blank=True, null=True)
    founder_name = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=300, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    # Stored as JSON: {"facebook": "https://...", "instagram": "https://..."}
    social_links = models.JSONField(blank=True, null=True, default=dict)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About"
        verbose_name_plural = "About (pages)"

    def __str__(self) -> str:
        return self.title or "About"


# ============================================================
#                       USER PROFILE
# ============================================================

class UserProfile(models.Model):
    """
    FEATURE: Extra user info.

    - Linked 1–1 with auth.User.
    - Stores phone + address captured at signup.
    - Visible on Profile page.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.user.username


# ============================================================
#                       REVIEWS
# ============================================================

class Review(models.Model):
    """
    FEATURE: Customer reviews.

    - Collected via Reviews page (ReviewForm).
    - Gender + rating choice used for small visual touches on UI.
    - Sorted newest first.
    """

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    RATING_CHOICES = [
        (1, "⭐☆☆☆☆"),
        (2, "⭐⭐☆☆☆"),
        (3, "⭐⭐⭐☆☆"),
        (4, "⭐⭐⭐⭐☆"),
        (5, "⭐⭐⭐⭐⭐"),
    ]

    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.rating}★)"


# ============================================================
#                RESERVATION / ORDER ONLINE FORM MODEL
# ============================================================

class Reservation(models.Model):
    """
    FEATURE: Simple "Order online / Reservation" record.

    Used by ReservationForm / checkout page mainly to capture customer
    contact + fulfilment info at time of order.
    """

    ORDER_TYPE_CHOICES = [
        ("delivery", "Delivery"),
        ("carryout", "Carryout"),
    ]

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    address = models.TextField(blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    store_location = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} - {self.order_type}"


# ============================================================
#                     MENU / CATEGORIES
# ============================================================

class MenuCategory(models.Model):
    """
    FEATURE: Logical grouping of menu items.

    e.g. "Burgers", "Sides", "Desserts".
    Used in menu filters & nav chips.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="(Optional) e.g. bi bi-basket",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class MenuItem(models.Model):
    """
    FEATURE: Individual dish / burger / side.

    - Linked to a MenuCategory.
    - Can have an image, veg/spicy flags, and a base price.
    - Additional `MenuItemSize` entries define S/M/L pricing.
    """

    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_veg = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu/", blank=True, null=True)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category__sort_order", "name"]

    def __str__(self) -> str:
        return self.name


# ============================================================
#                     MENU ITEM SIZES
# ============================================================

class MenuItemSize(models.Model):
    """
    FEATURE: Size-based pricing for a MenuItem.

    Example rows:
    - Margherita, S, 199
    - Margherita, M, 249
    """

    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
    ]

    item = models.ForeignKey(
        "MenuItem",
        on_delete=models.CASCADE,
        related_name="sizes",
    )
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        unique_together = ("item", "size")
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.item.name} ({self.get_size_display()}) - Rs {self.price}"


# ============================================================
#                  DEAL REQUIREMENTS
# ============================================================

class DealRequirement(models.Model):
    """
    FEATURE: Fine-grained deal rules.

    Each requirement links a Deal to:
    - a MenuCategory
    - an optional size (S/M/L)
    - a minimum quantity

    Used in checkout to enforce rules like:
      “Buy at least 2 Large burgers from 'Classics' category”.
    """

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.PROTECT,
        related_name="deal_requirements",
    )
    min_quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(
        max_length=1,
        choices=MenuItemSize.SIZE_CHOICES,
        blank=True,
        null=True,
        help_text="Optional size restriction (S/M/L). Leave blank for any size.",
    )

    class Meta:
        verbose_name = "Deal requirement"
        verbose_name_plural = "Deal requirements"

    def __str__(self) -> str:
        size_label = dict(MenuItemSize.SIZE_CHOICES).get(self.size, "Any size")
        return f"{self.deal.title} – {self.category.name} ({size_label}) × {self.min_quantity}+"


# ============================================================
#                        FAVORITES
# ============================================================

class Favorite(models.Model):
    """
    FEATURE: Per-user favourite items.

    - Used for the ♥ icon on menu cards.
    - Each row means “user likes this MenuItem”.
    - Unique per (user, item).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "item")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} ♥ {self.item.name}"


# ============================================================
#                        ORDERS
# ============================================================

ORDER_TYPE_CHOICES = [
    ("delivery", "Delivery"),
    ("carryout", "Carryout"),
]

ORDER_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("in_oven", "In oven"),
    ("on_the_way", "On the way"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
]


class Order(models.Model):
    """
    FEATURE: Stores a single checkout order.

    - Created in checkout_view after validating cart + deal code.
    - Linked to User for history & profile view.
    - Used by the order tracker page (status + progress bar).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # Snapshot of contact details at time of order
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()

    order_type = models.CharField(
        max_length=10,
        choices=ORDER_TYPE_CHOICES,
        default="delivery",
    )

    # Delivery / carryout details
    address = models.TextField(blank=True, null=True)
    store_location = models.CharField(max_length=80, blank=True, null=True)

    # --- Deal info (optional) ---------------------------------
    deal = models.ForeignKey(
        Deal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Deal applied at checkout, if any.",
    )
    deal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Deal code typed by the customer at checkout.",
    )
    deal_discount_amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total discount applied because of the deal.",
    )

    # Money fields (snapshot so later price changes don’t affect history)
    subtotal = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total of items before delivery/fees.",
    )
    delivery_fee = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default="pending",
        help_text="Drives the front-end order tracker steps.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Also doubles as a place to store "[ACK]" markers when
    # user has acknowledged a completed order in the tracker.
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        base = f"Order #{self.pk or 'NEW'}"
        if self.user:
            return f"{base} by {self.user.username}"
        return base


class OrderItem(models.Model):
    """
    FEATURE: Line item inside an Order.

    - Each row is one menu item (plus size) in a given order.
    - We denormalize price at time of order so later changes to MenuItem
      do not alter historical order totals.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    size = models.CharField(
        max_length=1,
        choices=MenuItemSize.SIZE_CHOICES,
        blank=True,
        null=True,
        help_text="Optional size code: S/M/L",
    )
    size_label = models.CharField(
        max_length=20,
        blank=True,
        help_text="Human-readable size at time of order (e.g. Small, Medium).",
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Price per unit at time of ordering.",
    )
    line_total = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    def __str__(self) -> str:
        return f"{self.quantity} × {self.item.name} ({self.order_id})"
