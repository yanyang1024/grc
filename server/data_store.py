from datetime import date, timedelta
from random import Random


def build_sales(days: int = 90) -> list[dict]:
    rng = Random(42)
    cats = ["A", "B", "C", "D"]
    regs = ["North", "South", "East", "West"]
    today = date.today()
    rows = []
    for i in range(days):
        d = today - timedelta(days=i)
        for c in cats:
            for r in regs:
                orders = rng.randint(5, 50)
                revenue = round(orders * rng.uniform(10, 50), 2)
                rows.append(
                    {
                        "date": d.isoformat(),
                        "category": c,
                        "region": r,
                        "orders": orders,
                        "revenue": revenue,
                    }
                )
    return rows


SALES_DATA = build_sales()

