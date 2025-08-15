from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio, time
from .scanner import Scanner, THRESHOLDS
from .db import get_db

app = FastAPI(title="MasterPig Scanner")
app.mount("/static", StaticFiles(directory="web/static"), name="static")

scanner: Scanner | None = None
scan_task: asyncio.Task | None = None

@app.post("/start_scan")
async def start_scan(xpub: str, max_gap: int = 20, concurrency: int = 32, follow_depth: int = 2):
    global scanner, scan_task
    if scan_task and not scan_task.done():
        return JSONResponse({"status": "already_running"})
    scanner = Scanner(max_gap=max_gap, concurrency=concurrency, follow_depth=follow_depth)
    scan_task = asyncio.create_task(scanner.scan_xpub(xpub))
    return {"status": "started"}

@app.post("/stop_scan")
async def stop_scan():
    global scanner, scan_task
    if scanner:
        scanner.stop()
    if scan_task:
        try:
            await scan_task
        except Exception:
            pass
    return {"status": "stopped"}

@app.get("/stats")
async def stats():
    if scanner:
        return scanner.stats
    return {}

@app.get("/metrics")
async def metrics():
    # Returns:
    # - per-bucket counts for minute/hour/day/week/month/year
    # - thresholds counts (tx > 1, >2, >50, ...)
    # - recently used counts (past hour/day/week/month/year)
    # - with_balance counts overall and recent
    now = int(time.time())
    db = await get_db()
    result = {
        "thresholds": {},
        "buckets": {},
        "recent_usage": {},
        "balances": {},
    }
    if not db:
        # fallback to in-memory snapshot
        if scanner:
            result["thresholds"] = {f"gt_{t}": scanner.stats.get(f"tx_gt_{t}", 0) for t in THRESHOLDS}
            base = {
                "addresses_scanned": scanner.stats.get("addresses_scanned", 0),
                "active_addresses": scanner.stats.get("active_addresses", 0),
                "with_balance": scanner.stats.get("with_balance", 0)
            }
            for g in ["minute","hour","day","week","month","year"]:
                result["buckets"][g] = base
        return result

    # thresholds
    pipeline = [
        {"$group": {
            "_id": None,
            **{f"gt_{t}": {"$sum": {"$cond": [{"$gt": ["$tx_count", t]}, 1, 0]}} for t in THRESHOLDS},
            "with_balance": {"$sum": {"$cond": [{"$gt": ["$balance", 0]}, 1, 0]}},
            "active": {"$sum": {"$cond": [{"$gt": ["$tx_count", 0]}, 1, 0]}},
            "total": {"$sum": 1}
        }}
    ]
    agg = [a async for a in db.addresses.aggregate(pipeline)]
    if agg:
        row = agg[0]
        result["thresholds"] = {k: int(v) for k, v in row.items() if k.startswith("gt_")}
        result["balances"]["overall"] = int(row.get("with_balance", 0))
        result["recent_usage"]["overall_active"] = int(row.get("active", 0))
        result["recent_usage"]["total_addresses"] = int(row.get("total", 0))

    # buckets (pull last 1 per granularity)
    buckets = {}
    async for doc in db.stats.find().sort("bucket", -1).limit(200):
        # organize by granularity tag
        b = doc["bucket"]
        gran = b.split(":")[0]
        buckets.setdefault(gran, doc)
    result["buckets"] = buckets

    # recent windows
    def ts_minus(days=0, hours=0, minutes=0):
        return now - (days*86400 + hours*3600 + minutes*60)

    windows = {
        "past_hour": ts_minus(hours=1),
        "past_day": ts_minus(days=1),
        "past_week": ts_minus(days=7),
        "past_month": ts_minus(days=30),
        "past_year": ts_minus(days=365),
    }
    recent = {}
    for name, ts in windows.items():
        cur = await db.addresses.count_documents({"last_seen": {"$gte": ts}, "tx_count": {"$gt": 0}})
        with_bal = await db.addresses.count_documents({"balance": {"$gt": 0}, "last_seen": {"$gte": ts}})
        recent[name] = {"active": int(cur), "with_balance": int(with_bal)}
    result["recent_usage"] = recent

    return result

@app.get("/", response_class=HTMLResponse)
async def index():
    return (open("web/index.html","r").read())
