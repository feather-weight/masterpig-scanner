import aiohttp, asyncio, time
from ..config import settings

TATUM_BASE = "https://api.tatum.io"

class TatumClient:
    """Uses Tatum v3 BTC endpoints for address txs and balance."""
    def __init__(self, session: aiohttp.ClientSession):
        self.s = session
        self.headers = {
            "x-api-key": settings.tatum_api_key or "",
            "User-Agent": settings.user_agent,
        }

    async def address_txs(self, address: str, page_size: int = 50, offset: int = 0, testnet: bool=False):
        # v3 endpoint for BTC address txs (works for testnet if supported)
        net = "bitcoin"
        url = f"{TATUM_BASE}/v3/{net}/transaction/address/{address}?pageSize={page_size}&offset={offset}"
        async with self.s.get(url, headers=self.headers, timeout=30) as r:
            if r.status >= 400:
                return []
            return await r.json()

    async def address_balance(self, address: str, testnet: bool=False):
        net = "bitcoin"
        url = f"{TATUM_BASE}/v3/{net}/address/balance/{address}"
        async with self.s.get(url, headers=self.headers, timeout=20) as r:
            if r.status >= 400:
                return None
            return await r.json()
