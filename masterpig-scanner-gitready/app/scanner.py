import asyncio, time, aiohttp
from collections import defaultdict
from typing import Iterable, List, Dict, Any, Set
from .derivation import derive_address, is_testnet
from .providers.tatum import TatumClient
from .providers.blockchair import BlockchairClient
from .db import get_db

THRESHOLDS = (1,2,50,100,500,1000,5000,10000)

def _floor_bucket(ts: int, gran: str) -> str:
    # gran in ["minute","hour","day","week","month","year"]
    import datetime as dt
    t = dt.datetime.utcfromtimestamp(ts)
    if gran == "minute":
        return t.strftime("minute:%Y%m%d%H%M")
    if gran == "hour":
        return t.strftime("hour:%Y%m%d%H")
    if gran == "day":
        return t.strftime("day:%Y%m%d")
    if gran == "week":
        # ISO week
        return t.strftime("week:%G%V")
    if gran == "month":
        return t.strftime("month:%Y%m")
    if gran == "year":
        return t.strftime("year:%Y")
    return f"raw:{ts}"

class Scanner:
    def __init__(self, max_gap: int = 20, concurrency: int = 32, follow_depth: int = 2, max_peers_per_tx: int = 6):
        self.max_gap = max_gap
        self.concurrency = concurrency
        self.follow_depth = follow_depth
        self.max_peers_per_tx = max_peers_per_tx
        self._running = False
        self.stats = defaultdict(int)

    async def _record_metrics(self, db, addr: str, tx_count: int, balance: int | None):
        now = int(time.time())
        # base address doc
        if db:
            await db.addresses.update_one(
                {"address": addr},
                {"$set": {
                    "address": addr,
                    "tx_count": tx_count,
                    "balance": balance if balance is not None else 0,
                    "last_seen": now if tx_count > 0 else None
                }},
                upsert=True
            )
            # stats buckets
            buckets = [_floor_bucket(now, g) for g in ["minute","hour","day","week","month","year"]]
            inc = { "addresses_scanned": 1 }
            if tx_count > 0:
                inc["active_addresses"] = 1
            for t in THRESHOLDS:
                if tx_count > t:
                    inc[f"tx_gt_{t}"] = 1
            if balance and balance > 0:
                inc["with_balance"] = 1
            for b in buckets:
                await db.stats.update_one({"bucket": b}, {"$inc": inc, "$setOnInsert": {"bucket": b}}, upsert=True)

    async def scan_xpub(self, xpub: str):
        self._running = True
        testnet = is_testnet(xpub)
        seen: Set[str] = set()
        sem = asyncio.Semaphore(self.concurrency)

        async with aiohttp.ClientSession() as s:
            tatum = TatumClient(s)
            blockchair = BlockchairClient(s)
            db = await get_db()

            async def fetch_and_follow(addr: str, depth: int):
                if not self._running or addr in seen:
                    return
                seen.add(addr)

                async def get_txs():
                    async with sem:
                        return await tatum.address_txs(addr) or []

                async def get_balance():
                    async with sem:
                        return await tatum.address_balance(addr)

                txs, balance_resp = await asyncio.gather(
                    get_txs(), get_balance(), return_exceptions=True
                )
                if isinstance(txs, Exception):
                    txs = []
                if isinstance(balance_resp, Exception):
                    balance_resp = None
                tx_count = len(txs)
                balance = None
                if isinstance(balance_resp, dict):
                    # Tatum returns {"incoming": "...","outgoing": "...","balance": "..."}
                    try:
                        raw_balance = balance_resp.get("balance", "0")
                        balance = int(float(raw_balance) * 1e8) if isinstance(raw_balance, str) else int(raw_balance)
                    except Exception:
                        balance = 0

                # in-memory counters (for when Mongo is not configured)
                self.stats["addresses_scanned"] += 1
                if tx_count > 0:
                    self.stats["active_addresses"] += 1
                for t in THRESHOLDS:
                    if tx_count > t:
                        self.stats[f"tx_gt_{t}"] += 1
                if balance and balance > 0:
                    self.stats["with_balance"] += 1

                # persist rolling metrics
                await self._record_metrics(db, addr, tx_count, balance)

                # Deep follow: pull peer addresses from Blockchair per-tx (limited fanout)
                if depth < self.follow_depth and tx_count > 0:
                    # We will query up to first 3 transactions for peers to limit API load
                    async def get_detail(tx_hash: str):
                        async with sem:
                            return await blockchair.tx_details(tx_hash)

                    detail_tasks = []
                    for tx in txs[:3]:
                        tx_hash = tx.get("hash") or tx.get("txHash") or tx.get("txid") or tx.get("id")
                        if tx_hash:
                            detail_tasks.append(get_detail(tx_hash))

                    details = await asyncio.gather(*detail_tasks, return_exceptions=True)
                    for detail in details:
                        if isinstance(detail, Exception) or not detail:
                            continue
                        peers = blockchair.extract_peer_addresses(detail, addr, limit=self.max_peers_per_tx)
                        await asyncio.gather(*(fetch_and_follow(p, depth + 1) for p in peers))

            # Kick off gap-limit derivation for both chains
            tasks = []
            for chain in (0, 1):
                for idx in range(0, self.max_gap):
                    addr = derive_address(xpub, chain, idx, testnet=testnet)
                    tasks.append(asyncio.create_task(fetch_and_follow(addr, 0)))

            await asyncio.gather(*tasks)

        self._running = False
        return dict(self.stats)

    def stop(self):
        self._running = False
