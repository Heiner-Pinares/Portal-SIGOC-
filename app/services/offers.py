from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


ALLOWED_PERIODS = {1, 3, 6, 12, 18, 24}


class ValidationError(ValueError):
    pass


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError("El valor del descuento no es válido") from exc


def calculate_preview(records, selected_keys, discount_type, discount_value, period, existing):
    if len(selected_keys) > 500:
        raise ValidationError("La selección supera el máximo de 500 servicios por lote")
    if discount_type not in {"fixed", "percent"}:
        raise ValidationError("Tipo de descuento no permitido")
    value = money(discount_value)
    if value <= 0:
        raise ValidationError("El descuento debe ser mayor que cero")
    try:
        period = int(period)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Periodo inválido") from exc
    if period not in ALLOWED_PERIODS:
        raise ValidationError("Periodo no permitido en la simulación")
    if discount_type == "percent" and value > 100:
        raise ValidationError("El porcentaje no puede superar 100")

    by_key = {record.key: record for record in records}
    unknown = set(selected_keys) - set(by_key)
    if unknown:
        raise ValidationError("La selección contiene registros ajenos a la campaña")
    if not selected_keys:
        raise ValidationError("Selecciona al menos un servicio")
    if len(selected_keys) != len(set(selected_keys)):
        raise ValidationError("La selección contiene llaves duplicadas")

    operations = []
    counts = {"new": 0, "update": 0, "unchanged": 0, "errors": 0}
    for key in selected_keys:
        record = by_key[key]
        gross = record.charge_with_tax
        discount = value if discount_type == "fixed" else (gross * value / Decimal("100")).quantize(Decimal("0.01"))
        if discount > gross:
            raise ValidationError(f"El descuento supera el cargo de {record.service_name}")
        new_charge = (gross - discount).quantize(Decimal("0.01"))
        current = existing.get(key)
        status = "new" if current is None else "update"
        if current and str(current.get("dscto")) == f"{discount:.2f}" and str(current.get("periodo", period)) == str(period):
            status = "unchanged"
        counts[status] += 1
        operations.append({
            "key": key, "campaign": record.campaign, "campaign_name": record.campaign_name,
            "plan": record.plan, "plan_name": record.plan_name, "sncode": record.sncode,
            "service_name": record.service_name, "original_charge": f"{gross:.2f}",
            "discount_type": discount_type, "discount_value": f"{discount:.2f}",
            "period": period, "new_charge": f"{new_charge:.2f}", "status": status,
        })
    return {"counts": counts, "operations": operations}

