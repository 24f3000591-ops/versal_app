```python
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Load telemetry data
DATA = json.loads(
    Path("q-vercel-latency.json").read_text(encoding="utf-8")
)


class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p=95):
    values = sorted(values)

    if not values:
        return 0.0

    k = (len(values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)

    if f == c:
        return values[f]

    return values[f] + (k - f) * (values[c] - values[f])


@app.options("/")
@app.options("/api")
async def options_handler():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/")
async def health():
    return {"status": "ok"}


@app.post("/")
async def check_latency(payload: LatencyRequest):
    result = {}

    for region_name in payload.regions:
        region = region_name.lower().strip()

        rows = [r for r in DATA if r["region"] == region]

        if not rows:
            continue

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        result[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 2),
            "p95_latency": round(percentile(latencies, 95), 2),
            "avg_uptime": round(sum(uptimes) / len(uptimes), 3),
            "breaches": sum(
                1
                for latency in latencies
                if latency > payload.threshold_ms
            ),
        }

    return {"regions": result}
```
