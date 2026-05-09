from flask import Flask, jsonify, render_template, request

from .data_engine import DataEngine


app = Flask(__name__)
engine = DataEngine()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/global-temp")
def api_global_temp():
    min_year_raw = request.args.get("min_year", default="1850")
    try:
        min_year = int(min_year_raw)
    except ValueError:
        return jsonify({"error": "min_year 必须是整数"}), 400

    try:
        df = engine.get_global_temp(min_year=min_year)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"service error:{e}"}), 500

    payload = {
        "min_year": min_year,
        "years": df["year"].astype(int).tolist(),
        "temps": df["temperature"].astype(float).round(1).tolist(),
        "count": len(df),
    }
    return jsonify(payload)


@app.get("/api/city-temp")
def api_city_temp():
    year_raw = request.args.get("year")
    if year_raw is None:
        return jsonify({"error": "year 是必填参数"}), 400

    try:
        year = int(year_raw)
    except ValueError:
        return jsonify({"error": "year 必须是整数"}), 400

    limit_raw = request.args.get("limit", default="20")
    try:
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit 必须是整数"}), 400

    try:
        df = engine.get_city_temp_by_year(year=year, limit=limit)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"service error:{e}"}), 500

    payload = {
        "year": year,
        "cities": df["City"].astype(str).tolist(),
        "temps": df["temperature"].astype(float).round(1).tolist(),
        "count": len(df),
    }
    return jsonify(payload)


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
    app.run(debug=True, host="0.0.0.0", port=5000)
    