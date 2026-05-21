import math
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_engine import DataEngine

app = FastAPI(title="全球气温可视化")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_PATH = BASE_DIR / "templates" / "index.html"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

engine = DataEngine()


@app.get("/")
async def index():
    return FileResponse(str(INDEX_PATH))


# ── 全球气温 ──────────────────────────────────────────────────────

@app.get("/api/global/annual")
async def api_global_annual(min_year: int = Query(1850, ge=0)):
    try:
        df = engine.get_global_annual(min_year=min_year)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "min_year": min_year,
        "years": df["year"].astype(int).tolist(),
        "land_avg": df["land_avg"].round(1).tolist(),
        "land_uncertainty": df["land_uncertainty"].round(3).tolist(),
        "land_max": df["land_max"].round(1).tolist(),
        "land_min": df["land_min"].round(1).tolist(),
        "land_ocean_avg": df["land_ocean_avg"].round(1).tolist(),
        "land_ocean_uncertainty": df["land_ocean_uncertainty"].round(3).tolist(),
        "count": len(df),
    }


@app.get("/api/global/anomaly")
async def api_global_anomaly(
    baseline_start: int = Query(1951, ge=0),
    baseline_end: int = Query(1980, ge=0),
):
    try:
        return engine.get_global_anomaly(baseline_start=baseline_start, baseline_end=baseline_end)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/global/monthly")
async def api_global_monthly():
    try:
        df = engine.get_global_monthly()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    temps = df["temperature"].tolist()
    return {
        "months": df["month"].astype(int).tolist(),
        "temps": [round(t, 1) if not (isinstance(t, float) and math.isnan(t)) else None for t in temps],
    }


@app.get("/api/global/seasonal-anomaly")
async def api_global_seasonal_anomaly(min_year: int = Query(1900, ge=0)):
    try:
        return engine.get_seasonal_anomaly(min_year=min_year)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 国家数据 ──────────────────────────────────────────────────────

@app.get("/api/country/annual")
async def api_country_annual(year: int = Query(..., ge=0)):
    try:
        df = engine.get_country_annual(year=year)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "year": year,
        "countries": df["Country"].tolist(),
        "temps": df["temperature"].round(1).tolist(),
        "count": len(df),
    }


# ── 城市数据 ──────────────────────────────────────────────────────

@app.get("/api/city-temp")
async def api_city_temp(year: int = Query(..., ge=0), limit: int = Query(20, ge=1, le=100)):
    try:
        df = engine.get_city_temp_by_year(year=year, limit=limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "year": year,
        "cities": df["City"].astype(str).tolist(),
        "temps": df["temperature"].astype(float).round(1).tolist(),
        "count": len(df),
    }


@app.get("/api/city/latband")
async def api_city_latband(min_year: int = Query(1850, ge=0)):
    try:
        df = engine.get_city_latband(min_year=min_year)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    bands = ["tropical", "temperate", "polar"]
    band_labels = {"tropical": "热带", "temperate": "温带", "polar": "寒带"}
    years = sorted(df["year"].unique().astype(int).tolist())

    result: dict = {"min_year": min_year, "years": years}
    for band in bands:
        subset = df[df["band"] == band]
        temp_map = dict(zip(subset["year"], subset["temperature"]))
        result[band] = [
            round(float(temp_map[y]), 1)
            if y in temp_map and not (isinstance(temp_map[y], float) and math.isnan(temp_map[y]))
            else None
            for y in years
        ]
        result[f"{band}_label"] = band_labels[band]

    result["count"] = len(years)
    return result


@app.get("/api/state-temp")
def api_state_temp():
    year_raw = request.args.get("year")
    if year_raw is None:
        return jsonify({"error": "year 是必填参数"}), 400

    country = request.args.get("country", default="United States").strip()
    if not country:
        return jsonify({"error": "country 是必填参数"}), 400

    try:
        year = int(year_raw)
    except ValueError:
        return jsonify({"error": "year 必须是整数"}), 400

    limit_raw = request.args.get("limit", default="15")
    try:
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit 必须是整数"}), 400

    try:
        df = engine.get_state_temp_by_year(year=year, country=country, limit=limit)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"service error:{e}"}), 500

    payload = {
        "year": year,
        "country": country,
        "states": df["State"].astype(str).tolist(),
        "temps": df["temperature"].astype(float).round(1).tolist(),
        "count": len(df),
    }
    return jsonify(payload)


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=5000, reload=True)
