"""
Material reference rates (live USD/INR + indicative ₹/unit).
"""

from fastapi import APIRouter, Query

from app.core.material_market_rates import build_material_unit_rates
from app.models.prediction_models import MaterialUnitRate, FxMeta, MaterialRatesResponse

router = APIRouter()


@router.get("/material-rates", response_model=MaterialRatesResponse, tags=["Materials"])
async def get_material_rates(
    materials: str = Query(
        default="",
        description="Comma-separated material names (e.g. from IFC extraction). Empty → Unknown.",
    ),
):
    """Return indicative ₹/unit rows for the given material labels with a fresh FX snapshot."""
    names = [m.strip() for m in materials.split(",") if m.strip()]
    if not names:
        names = ["Unknown"]

    rows_raw, fx_meta_raw = await build_material_unit_rates(names)

    return MaterialRatesResponse(
        material_unit_rates=[MaterialUnitRate(**r) for r in rows_raw],
        fx_meta=FxMeta(
            usd_inr=fx_meta_raw["usd_inr"],
            reference_usd_inr=fx_meta_raw["reference_usd_inr"],
            fx_source=fx_meta_raw["fx_source"],
            fx_rate_date=fx_meta_raw.get("fx_rate_date"),
            fetched_at_utc=fx_meta_raw["fetched_at_utc"],
        ),
    )
