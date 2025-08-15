import aiohttp

BC_BASE = "https://api.blockchair.com/bitcoin"

class BlockchairClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.s = session

    async def address_overview(self, address: str):
        url = f"{BC_BASE}/dashboards/address/{address}"
        async with self.s.get(url, timeout=30) as r:
            if r.status >= 400:
                return None
            return await r.json()

    async def xpub_overview(self, xpub: str):
        url = f"{BC_BASE}/dashboards/xpub/{xpub}"
        async with self.s.get(url, timeout=30) as r:
            if r.status >= 400:
                return None
            return await r.json()

    async def tx_details(self, tx_hash: str):
        url = f"{BC_BASE}/dashboards/transaction/{tx_hash}"
        async with self.s.get(url, timeout=30) as r:
            if r.status >= 400:
                return None
            return await r.json()

    def extract_peer_addresses(self, tx_detail: dict, focus_addr: str, limit: int = 6):
        # Returns a small set of peer addresses (inputs and outputs) excluding focus_addr
        peers = []
        try:
            data = tx_detail.get("data", {})
            # The key is the tx hash; grab its record
            rec = next(iter(data.values()))
            inputs = rec.get("inputs", [])
            outputs = rec.get("outputs", [])
            for x in inputs + outputs:
                a = x.get("recipient") or x.get("recipient_address") or x.get("address")
                if a and a != focus_addr and a not in peers:
                    peers.append(a)
                if len(peers) >= limit:
                    break
        except Exception:
            return peers[:limit]
        return peers[:limit]
