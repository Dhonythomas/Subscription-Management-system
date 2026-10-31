from decimal import Decimal

from apps.discounts.models import Discount, DiscountUsage
from apps.platform.money import quantize_money


def apply_invoice_discounts(
    *, invoice, subscription, lines, product_ids, billing_date
):
    discounts = list(
        Discount.objects.select_for_update()
        .prefetch_related("products")
        .filter(
            is_active=True,
            start_date__lte=billing_date,
            end_date__gte=billing_date,
        )
        .order_by("id")
    )
    subtotal = sum((line.amount for line in lines), Decimal("0.00"))
    total_quantity = sum((line.quantity for line in lines), Decimal("0.00"))
    total_discount = Decimal("0.00")
    applied = []

    for discount in discounts:
        if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
            continue
        if discount.min_amount is not None and subtotal < discount.min_amount:
            continue
        if discount.min_qty is not None and total_quantity < discount.min_qty:
            continue

        if discount.scope == Discount.Scope.PRODUCT:
            target_products = {product.pk for product in discount.products.all()}
            target_indexes = [
                index
                for index, product_id in enumerate(product_ids)
                if product_id in target_products
            ]
        else:
            target_indexes = list(range(len(lines)))

        base = sum(
            (lines[index].amount - lines[index].discount for index in target_indexes),
            Decimal("0.00"),
        )
        if base <= 0:
            continue

        if discount.type == Discount.Type.FIXED:
            raw_discount = discount.value
        else:
            raw_discount = base * discount.value / Decimal("100")
        discount_amount = quantize_money(min(raw_discount, base))
        if discount_amount <= 0:
            continue

        remaining = discount_amount
        for position, index in enumerate(target_indexes):
            if position == len(target_indexes) - 1:
                share = remaining
            else:
                line_base = lines[index].amount - lines[index].discount
                share = quantize_money(discount_amount * line_base / base)
                share = min(share, remaining)
            lines[index].discount = quantize_money(lines[index].discount + share)
            remaining = quantize_money(remaining - share)

        for line in lines:
            line.save(update_fields=["discount", "updated_at"])

        DiscountUsage.objects.create(
            discount=discount, subscription=subscription, invoice=invoice
        )
        discount.used_count += 1
        discount.save(update_fields=["used_count", "updated_at"])
        total_discount += discount_amount
        applied.append(discount)

    return quantize_money(total_discount), applied
