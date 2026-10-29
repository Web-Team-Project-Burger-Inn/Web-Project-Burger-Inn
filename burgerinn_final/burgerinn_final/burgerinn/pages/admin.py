from django.contrib import admin

from .models import (
    Deal,
    About,
    UserProfile,
    MenuCategory,
    MenuItem,
    MenuItemSize,
    Review,
    Order,
    OrderItem,
    Reservation,
    DealRequirement,   # deal “rules” per category/size
)

# ============================================================
#                    USER PROFILE
# ============================================================

# Simple registration so you can see/edit a user's profile
admin.site.register(UserProfile)


# ============================================================
#                    ABOUT PAGE CONTENT
# ============================================================
@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    """
    Admin config for the single 'About' page content block.
    Lets staff update description, founder, contact info, etc.
    """
    list_display = ("title", "founder_name", "founded_year", "last_updated")
    list_display_links = ("title",)
    readonly_fields = ("last_updated",)
    search_fields = ("title", "founder_name", "description")


# ============================================================
#                    DEALS + REQUIREMENTS
# ============================================================

class DealRequirementInline(admin.TabularInline):
    """
    Inline to define category/size-based requirements for a deal.

    Example usage in admin:
      - 1 Classic Burger (Medium)
      - 1 Side (any size)
      - 2 Drinks

    The checkout logic will validate these requirements and calculate
    the discount only on matching cart items.
    """
    model = DealRequirement
    extra = 1
    fields = ("category", "size", "min_quantity")
    autocomplete_fields = ("category",)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    """
    Admin for promotional deals (e.g. combo offers, student specials).

    Key points:
    - 'code' is what customers type at checkout.
    - 'price' vs 'original_price' automatically computes discount%.
    - Requirements are managed from DealRequirementInline.
    """
    list_display = (
        "title",
        "code",              # deal code shown in admin list
        "price",
        "original_price",
        "discount_percentage",
        "start_date",
        "end_date",
        "deal_type",
    )
    list_filter = ("deal_type", "start_date", "end_date")
    search_fields = ("title", "description", "code")
    inlines = [DealRequirementInline]   # attach multi-category / size rules


# ============================================================
#                    MENU CATEGORIES
# ============================================================
@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    """
    Categories like 'Classic Burgers', 'Sides', 'Drinks', etc.
    """
    list_display = ("name", "slug", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


# ============================================================
#                    MENU ITEMS + SIZES
# ============================================================

class MenuItemSizeInline(admin.TabularInline):
    """
    Inline for per-item size pricing (S/M/L) under each MenuItem.
    """
    model = MenuItemSize
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """
    Admin for individual menu items (burgers, sides, drinks).
    Size-specific prices are managed via MenuItemSizeInline.
    """
    list_display = ("name", "category", "price", "is_available", "is_veg", "is_spicy")
    list_filter = ("category", "is_available", "is_veg", "is_spicy")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MenuItemSizeInline]


# ============================================================
#                    REVIEWS
# ============================================================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Admin for customer reviews shown on the Reviews page.
    """
    list_display = ("name", "gender", "rating", "created_at")
    list_filter = ("gender", "rating", "created_at")
    search_fields = ("name", "comment")


# ============================================================
#                    RESERVATIONS / CHECKOUT FORM
# ============================================================
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Reservations / checkout form submissions.
    Mainly for viewing what customers entered at checkout.
    """
    list_display = ("full_name", "order_type", "phone", "created_at")
    list_filter = ("order_type", "created_at")
    search_fields = ("full_name", "phone", "email")


# ============================================================
#                    ORDER MANAGEMENT
# ============================================================

class OrderItemInline(admin.TabularInline):
    """
    Read-only inline list of line items inside each Order.

    Note: we keep these readonly so that staff can't accidentally
    change historical order details (prices, quantities).
    """
    model = OrderItem
    extra = 0
    readonly_fields = (
        "item",
        "size_label",
        "quantity",
        "unit_price",
        "line_total",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin interface for orders created via the cart/checkout flow.

    - Staff can adjust status from the list view (pending → in_oven → …).
    - Deal code, discount and totals are read-only and come from checkout logic.
    - After an order is 'completed', all fields become read-only to avoid edits.
    """
    list_display = (
        "id",
        "user",
        "full_name",
        "phone",
        "order_type",
        "subtotal",
        "delivery_fee",
        "deal_discount_amount",  # how much was discounted
        "total",
        "status",
        "created_at",
        "deal_code",
    )
    list_filter = ("status", "order_type", "created_at")
    search_fields = ("full_name", "phone", "email", "user__username", "deal_code")
    list_editable = ("status",)  # change status directly in list view
    inlines = [OrderItemInline]

    # Base readonly fields (things staff shouldn't touch manually)
    readonly_fields = (
        "user",
        "full_name",
        "phone",
        "email",
        "order_type",
        "address",
        "store_location",
        "subtotal",
        "delivery_fee",
        "deal",
        "deal_code",
        "deal_discount_amount",
        "total",
        "created_at",
        "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Once an order is marked as 'completed', lock ALL fields
        (including status and notes).

        Before completion:
        - `status` remains editable (both list + detail view).
        - `notes` can be edited to add staff comments.
        """
        base = list(super().get_readonly_fields(request, obj))

        if obj and obj.status == "completed":
            # make every model field read-only on completed orders
            all_fields = [f.name for f in self.model._meta.fields]
            return list(set(base + all_fields))

        # While not completed, allow editing status + notes in the detail view
        # (status is list_editable so it must NOT be read-only here)
        return base
