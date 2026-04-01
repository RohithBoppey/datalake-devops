def generate_orders(N=20) -> list[dict]:
    """Generate N sample orders."""
    statuses = ["created", "processing", "shipped", "delivered", "cancelled"]
    orders = []
    for i in range(1, N):
        orders.append({
            "order_id": f"ORD-{i:04d}",
            "status": statuses[i % len(statuses)],
            "amount": 100 + (i * 37) % 900,
        })
    return orders