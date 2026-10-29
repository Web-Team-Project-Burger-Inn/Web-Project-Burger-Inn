from pages.cart import build_cart_context


def cart_summary(request):
    """
    Context processor that exposes a small cart summary
    (item count + subtotal) to all templates.

    Used mainly in the navbar to show:
      - how many items are currently in the cart
      - the current cart subtotal

    It reuses the same helper as the full cart page so we don't
    duplicate pricing logic.
    """
    try:
        # Reuse the shared cart-building helper
        ctx = build_cart_context(request)

        # Only return the minimal data needed for global UI elements
        return {
            "cart_count": ctx["cart_total_qty"],   # total quantity of items
            "cart_subtotal": ctx["cart_subtotal"],  # subtotal before delivery/deals
        }
    except Exception:
        # If anything goes wrong (e.g. corrupted session),
        # fail safely so the rest of the page still renders.
        return {
            "cart_count": 0,
            "cart_subtotal": 0,
        }
