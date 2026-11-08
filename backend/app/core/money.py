"""Helpers de dinheiro — Decimal com quantização HALF_UP em 2 casas."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

MONEY_QUANTIZE = Decimal("0.01")


def quantize_money(value: Decimal | float | int | str) -> Decimal:
    """Converte para Decimal e arredonda com ROUND_HALF_UP em 2 casas."""
    if isinstance(value, Decimal):
        dec = value
    else:
        # str() evita artefatos de float binário na entrada (ex.: 19.9)
        dec = Decimal(str(value))
    return dec.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def money_to_float(value: Decimal) -> float:
    """Serializa dinheiro como número JSON com exatamente 2 casas (contrato front)."""
    return float(quantize_money(value))


def _parse_money(value: object) -> Decimal:
    if value is None:
        raise TypeError("Valor monetário não pode ser nulo")
    if isinstance(value, Decimal):
        return quantize_money(value)
    if isinstance(value, (int, float, str)):
        return quantize_money(value)
    raise TypeError(f"Tipo inválido para valor monetário: {type(value)!r}")


# Tipo Pydantic: aceita number/string, guarda Decimal quantizado, serializa como number.
MoneyDecimal = Annotated[
    Decimal,
    BeforeValidator(_parse_money),
    PlainSerializer(money_to_float, return_type=float, when_used="json"),
]
