from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, status

from src.models import Parameter, Unit
from src.parameter_repository import ParameterRepository
from src.unit_repository import UnitRepository

SALINITY_PARAMETER = "salinity"
PHOSPHATE_PARAMETER = "phosphate"
TEMPERATURE_PARAMETER = "temperature"
CALCIUM_PARAMETER = "calcium"
AMMONIA_PARAMETER = "ammonia"
NITRITE_PARAMETER = "nitrite"
NITRATE_PARAMETER = "nitrate"
PH_PARAMETER = "ph"
ALKALINITY_PARAMETER = "alkalinity"
MAGNESIUM_PARAMETER = "magnesium"

SUPPORTED_SALINITY_UNITS = {"ppt", "sg"}
SUPPORTED_PHOSPHATE_UNITS = {"ppm"}
SUPPORTED_TEMPERATURE_UNITS = {"celsius", "fahrenheit"}
SUPPORTED_CALCIUM_UNITS = {"ppm"}
SUPPORTED_AMMONIA_UNITS = {"mg/l"}
SUPPORTED_NITRITE_UNITS = {"ppm"}
SUPPORTED_NITRATE_UNITS = {"ppm"}
SUPPORTED_PH_UNITS = {"ph"}
SUPPORTED_ALKALINITY_UNITS = {"dkh"}
SUPPORTED_MAGNESIUM_UNITS = {"ppm"}

SG_TO_PPT_FACTOR = 1325.76  # conversion factor valid at a typical reef aquarium temperature of 25°C
MAX_SALINITY_PPT = 100.0
MIN_SALINITY_SG = 1.0
MAX_SALINITY_SG = 1.04
MAX_PHOSPHATE_PPM = 100.0
MIN_TEMPERATURE_CELSIUS = 0.0
MAX_TEMPERATURE_CELSIUS = 45.0
MIN_CALCIUM_PPM = 0.0
MAX_CALCIUM_PPM = 1000.0
MIN_AMMONIA_MGL = 0.0
MAX_AMMONIA_MGL = 50.0
MIN_NITRITE_PPM = 0.0
MAX_NITRITE_PPM = 50.0
MIN_NITRATE_PPM = 0.0
MAX_NITRATE_PPM = 500.0
MIN_PH = 0.0
MAX_PH = 14.0
MIN_ALKALINITY_DKH = 0.0
MAX_ALKALINITY_DKH = 30.0
MIN_MAGNESIUM_PPM = 0.0
MAX_MAGNESIUM_PPM = 2000.0


def _to_ppt(value: float, unit: str) -> float:
    if unit == "ppt":
        return value
    return (value - 1.0) * SG_TO_PPT_FACTOR


def fahrenheit_to_celsius(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def _to_celsius(value: float, unit: str) -> float:
    if unit == "celsius":
        return value
    return fahrenheit_to_celsius(value)


def _identity(value: float, unit: str) -> float:
    return value


def _validate_salinity_value(value: float, unit: str) -> None:
    if unit == "ppt" and value > MAX_SALINITY_PPT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Salinity value in ppt must be less than or equal to 100",
        )
    if unit == "sg" and not (MIN_SALINITY_SG <= value <= MAX_SALINITY_SG):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Salinity value in sg must be between 1.0 and 1.04",
        )


def _validate_temperature_value(value: float, unit: str) -> None:
    canonical_value = _to_celsius(value, unit)
    if not (MIN_TEMPERATURE_CELSIUS <= canonical_value <= MAX_TEMPERATURE_CELSIUS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Temperature value must be between 0 and 45 degrees Celsius",
        )


def _range_validator(
    min_value: float, max_value: float, error_detail: str
) -> Callable[[float, str], None]:
    def _validate(value: float, unit: str) -> None:
        if not (min_value <= value <= max_value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=error_detail,
            )

    return _validate


@dataclass(frozen=True)
class ParameterRule:
    supported_units: frozenset[str]
    canonical_unit: str
    canonical_range: tuple[float, float]
    canonicalize: Callable[[float, str], float]
    validate_value: Callable[[float, str], None]
    unit_error: str


PARAMETER_RULES: dict[str, ParameterRule] = {
    SALINITY_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_SALINITY_UNITS),
        canonical_unit="ppt",
        canonical_range=(0.0, MAX_SALINITY_PPT),
        canonicalize=_to_ppt,
        validate_value=_validate_salinity_value,
        unit_error="Salinity unit must be one of: ppt, sg",
    ),
    TEMPERATURE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_TEMPERATURE_UNITS),
        canonical_unit="celsius",
        canonical_range=(MIN_TEMPERATURE_CELSIUS, MAX_TEMPERATURE_CELSIUS),
        canonicalize=_to_celsius,
        validate_value=_validate_temperature_value,
        unit_error="Temperature unit must be one of: celsius, fahrenheit",
    ),
    PHOSPHATE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_PHOSPHATE_UNITS),
        canonical_unit="ppm",
        canonical_range=(0.0, MAX_PHOSPHATE_PPM),
        canonicalize=_identity,
        validate_value=_range_validator(
            0.0, MAX_PHOSPHATE_PPM, "Phosphate value in ppm must be less than or equal to 100"
        ),
        unit_error="Phosphate unit must be: ppm",
    ),
    CALCIUM_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_CALCIUM_UNITS),
        canonical_unit="ppm",
        canonical_range=(MIN_CALCIUM_PPM, MAX_CALCIUM_PPM),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_CALCIUM_PPM,
            MAX_CALCIUM_PPM,
            f"Calcium value in ppm must be between {MIN_CALCIUM_PPM} and {MAX_CALCIUM_PPM}",
        ),
        unit_error="Calcium unit must be: ppm",
    ),
    AMMONIA_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_AMMONIA_UNITS),
        canonical_unit="mg/L",
        canonical_range=(MIN_AMMONIA_MGL, MAX_AMMONIA_MGL),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_AMMONIA_MGL,
            MAX_AMMONIA_MGL,
            f"Ammonia value in mg/L must be between {MIN_AMMONIA_MGL} and {MAX_AMMONIA_MGL}",
        ),
        unit_error="Ammonia unit must be: mg/L",
    ),
    NITRITE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_NITRITE_UNITS),
        canonical_unit="ppm",
        canonical_range=(MIN_NITRITE_PPM, MAX_NITRITE_PPM),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_NITRITE_PPM,
            MAX_NITRITE_PPM,
            f"Nitrite value in ppm must be between {MIN_NITRITE_PPM} and {MAX_NITRITE_PPM}",
        ),
        unit_error="Nitrite unit must be: ppm",
    ),
    NITRATE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_NITRATE_UNITS),
        canonical_unit="ppm",
        canonical_range=(MIN_NITRATE_PPM, MAX_NITRATE_PPM),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_NITRATE_PPM,
            MAX_NITRATE_PPM,
            f"Nitrate value in ppm must be between {MIN_NITRATE_PPM} and {MAX_NITRATE_PPM}",
        ),
        unit_error="Nitrate unit must be: ppm",
    ),
    PH_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_PH_UNITS),
        canonical_unit="pH",
        canonical_range=(MIN_PH, MAX_PH),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_PH, MAX_PH, f"pH value must be between {MIN_PH} and {MAX_PH}"
        ),
        unit_error="pH unit must be: pH",
    ),
    ALKALINITY_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_ALKALINITY_UNITS),
        canonical_unit="dKH",
        canonical_range=(MIN_ALKALINITY_DKH, MAX_ALKALINITY_DKH),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_ALKALINITY_DKH,
            MAX_ALKALINITY_DKH,
            f"Alkalinity value in dKH must be between {MIN_ALKALINITY_DKH} and {MAX_ALKALINITY_DKH}",
        ),
        unit_error="Alkalinity unit must be: dKH",
    ),
    MAGNESIUM_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_MAGNESIUM_UNITS),
        canonical_unit="ppm",
        canonical_range=(MIN_MAGNESIUM_PPM, MAX_MAGNESIUM_PPM),
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_MAGNESIUM_PPM,
            MAX_MAGNESIUM_PPM,
            f"Magnesium value in ppm must be between {MIN_MAGNESIUM_PPM} and {MAX_MAGNESIUM_PPM}",
        ),
        unit_error="Magnesium unit must be: ppm",
    ),
}

SUPPORTED_PARAMETERS = frozenset(PARAMETER_RULES.keys())


def normalize_parameter(value: str, parameter_repo: ParameterRepository) -> Parameter:
    normalized = value.strip().lower()
    parameter = parameter_repo.get_by_slug(normalized)
    if parameter is None or normalized not in PARAMETER_RULES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Parameter must be one of: {', '.join(PARAMETER_RULES)}",
        )
    return parameter


def canonicalize_measurement(parameter: str, value: float, unit: str) -> tuple[float, str]:
    rule = PARAMETER_RULES[parameter]
    return rule.canonicalize(value, unit), rule.canonical_unit


def validate_measurement_payload(
    parameter: Parameter, value: float, unit: str, unit_repo: UnitRepository
) -> Unit:
    rule = PARAMETER_RULES[parameter.slug]
    unit_row = unit_repo.get_by_unit(unit)
    if unit_row is None or not unit_repo.is_unit_valid_for_parameter(parameter.id, unit_row.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=rule.unit_error,
        )
    rule.validate_value(value, unit)
    return unit_row
