from decimal import Decimal
from typing import Dict, Any, Tuple

from .models import MenuItem, MenuItemSize

# Session key under which we store the cart dictionary.
# Shape in session:
#   request.session["cart"] = {
#       "itemId:size": {"qty": int},
#       ...
#   }
CART_SESSION_KEY = "cart"

# Separator used between item_id and size when building the cart key.
SIZE_SEP = ":"

# Token used when an item has no size (e.g. sides, drinks).
NO_SIZE_TOKEN = "-"


def _key(item_id: int, size: str | None) -> str:
    """
    Build the internal session key from item_id and size.

    Examples:
        _key(5, "M")   -> "5:M"
        _key(5, None)  -> "5:-"
    """
    return f"{int(item_id)}{SIZE_SEP}{(size or NO_SIZE_TOKEN)}"


def _split_key(k: str) -> Tuple[int, str | None]:
    """
    Reverse of _key: turn the session key back into (item_id, size).

    Examples:
        "5:M" -> (5, "M")
        "5:-" -> (5, None)
    """
    parts = k.split(SIZE_SEP, 1)
    iid = int(parts[0])
    size = parts[1] if len(parts) > 1 and parts[1] != NO_SIZE_TOKEN else None
    return iid, size


def _get_cart(session) -> Dict[str, Dict[str, int]]:
    """
    Ensure there is a cart dict in the session and return it.

    Shape:
        {
          "itemId:size": {"qty": int},
          ...
        }
    """
    return session.setdefault(CART_SESSION_KEY, {})


def add_item(request, item_id: int, size: str | None, qty: int = 1) -> None:
    """
    Increase (or create) a cart line by qty.

    - If the line already exists, increment its quantity.
    - If not, create it with the given quantity (at least 1).
    """
    cart = _get_cart(request.session)
    k = _key(item_id, size)

    if k in cart:
        cart[k]["qty"] += qty
    else:
        cart[k] = {"qty": max(1, qty)}

    # Mark the session as modified so Django saves it.
    request.session.modified = True


def set_qty(request, item_id: int, size: str | None, qty: int) -> None:
    """
    Set the quantity for a cart line.

    - If qty <= 0, the line is removed.
    - Otherwise, the line is set to the given qty (no increment).
    """
    cart = _get_cart(request.session)
    k = _key(item_id, size)

    if qty <= 0:
        cart.pop(k, None)
    else:
        cart[k] = {"qty": qty}

    request.session.modified = True


def remove_item(request, item_id: int, size: str | None) -> None:
    """
    Remove a single cart line completely, regardless of its quantity.
    """
    cart = _get_cart(request.session)
    cart.pop(_key(item_id, size), None)
    request.session.modified = True


def clear(request) -> None:
    """
    Clear the whole cart for the current session.
    """
    request.session[CART_SESSION_KEY] = {}
    request.session.modified = True


def _resolve_price(item: MenuItem, size: str | None) -> Tuple[Decimal, str]:
    """
    Returns (price, size_label) for the given item and size.

    Logic:
      - If a size code is provided (e.g. "S", "M", "L"), look up the
        corresponding MenuItemSize row and use its price + label.
      - If no size or size row is found, fall back to the base item.price.

    Returns:
      (unit_price, size_label)
        - unit_price: Decimal
        - size_label: e.g. "Medium" or "" if no size
    """
    if size:
        try:
            v = MenuItemSize.objects.get(item=item, size=size)
            return (v.price or Decimal("0.00")), v.get_size_display()
        except MenuItemSize.DoesNotExist:
            # fall back to base price if the specific size row is missing
            pass

    return (item.price or Decimal("0.00")), (size or "")


def build_cart_context(request) -> Dict[str, Any]:
    """
    Build a context dict for templates containing:

      - cart_items: list of cart lines, each with:
          {
            "item": MenuItem,
            "size": "S" | "M" | "L" | None,
            "size_label": "Small"/"Medium"/"Large"/"",
            "qty": int,
            "price": Decimal,        # unit price
            "line_total": Decimal,   # price * qty
          }

      - cart_subtotal: Decimal
          Sum of all line_total values (no deals, no delivery).

      - cart_total_qty: int
          Total number of items across all lines.

    This function is used:
      - on the main Cart page
      - in checkout
      - indirectly by the cart_summary context processor for the navbar.
    """
    cart = _get_cart(request.session)

    # Decode all session keys into (item_id, size) pairs
    parsed = [_split_key(k) for k in cart.keys()]
    ids = [iid for iid, _ in parsed]

    # Fetch all MenuItem objects in ONE query to avoid N+1 queries.
    items = {
        m.id: m
        for m in MenuItem.objects.filter(id__in=ids).select_related("category")
    }

    out = []
    subtotal = Decimal("0.00")
    total_qty = 0

    # Build each cart line with full item details + pricing
    for k, v in cart.items():
        iid, size = _split_key(k)
        item = items.get(iid)
        if not item:
            # If an item was deleted from DB but still in session, skip it.
            continue

        qty = int(v.get("qty", 0))
        if qty <= 0:
            continue

        unit_price, size_label = _resolve_price(item, size)
        line_total = unit_price * qty

        subtotal += line_total
        total_qty += qty

        out.append(
            {
                "item": item,
                "size": size,              # raw size code, e.g. "M" or None
                "size_label": size_label,  # human text, e.g. "Medium"
                "qty": qty,
                "price": unit_price,
                "line_total": line_total,
            }
        )

    return {
        "cart_items": out,
        "cart_subtotal": subtotal,
        "cart_total_qty": total_qty,
    }
