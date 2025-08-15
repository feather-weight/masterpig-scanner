from bip_utils import Bip44, Bip84, Bip49, Bip32Slip10Secp256k1, Bip32KeyError, Bip32PublicKey
from bip_utils import Bip44Coins, Bip49Coins, Bip84Coins, Bip32Utils, Bech32Encoder
import re

# Map extended pubkey prefixes to coin standards
def parse_extended_pubkey(xkey: str):
    xkey = xkey.strip()
    if xkey.startswith(("xpub", "tpub")):
        return "bip44", xkey
    if xkey.startswith(("ypub",)):
        return "bip49", xkey
    if xkey.startswith(("zpub",)):
        return "bip84", xkey
    raise ValueError("Unsupported extended pubkey prefix")

def derive_address(xkey: str, chain: int, index: int, testnet: bool=False) -> str:
    kind, _ = parse_extended_pubkey(xkey)
    if kind == "bip44":
        ctx = Bip44Coins.BITCOIN_TESTNET if testnet else Bip44Coins.BITCOIN
        return Bip44.FromExtendedKey(xkey, ctx).Change(chain).AddressIndex(index).PublicKey().ToAddress()
    if kind == "bip49":
        ctx = Bip49Coins.BITCOIN_TESTNET if testnet else Bip49Coins.BITCOIN
        return Bip49.FromExtendedKey(xkey, ctx).Change(chain).AddressIndex(index).PublicKey().ToAddress()
    if kind == "bip84":
        ctx = Bip84Coins.BITCOIN_TESTNET if testnet else Bip84Coins.BITCOIN
        return Bip84.FromExtendedKey(xkey, ctx).Change(chain).AddressIndex(index).PublicKey().ToAddress()
    raise ValueError("Unknown kind")

def is_testnet(xkey: str) -> bool:
    return xkey.startswith("tpub")
