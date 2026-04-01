import random
from datetime import datetime, timezone

STATUSES = ["created", "paid", "shipped", "delivered", "cancelled"]


def generate_order(order_num: int) -> dict:
    """Generate a single order event for a given order number."""
    return {
        "order_id": f"ORD-{order_num:04d}",
        "status": random.choice(STATUSES),
        "amount": round(random.uniform(100, 999), 2),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_orders(n: int = 20) -> list[dict]:
    """Generate n sample orders with IDs ORD-0001 through ORD-{n}."""
    return [generate_order(i) for i in range(1, n + 1)]
