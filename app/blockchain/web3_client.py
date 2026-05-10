# app/blockchain/web3_client.py
import time
import os
import json

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from config import Config
from app.utils.logger import log

# ─── ABI ──────────────────────────────────────────────────────────────────────
CONTRACT_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "bytes32", "name": "msgHash",   "type": "bytes32"},
            {"indexed": True,  "internalType": "address", "name": "sender",    "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "HashStored",
        "type": "event"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "msgHash", "type": "bytes32"}],
        "name": "storeHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "msgHash", "type": "bytes32"}],
        "name": "checkHash",
        "outputs": [
            {"internalType": "bool",    "name": "exists_",    "type": "bool"},
            {"internalType": "address", "name": "sender_",    "type": "address"},
            {"internalType": "uint256", "name": "timestamp_", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalHashes",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
        "name": "getHashAt",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ─── Mock хранилище на диске ──────────────────────────────────────────────────
_MOCK_FILE = os.path.join(Config.KEYS_DIR, "mock_registry.json")


def _load_mock_registry() -> dict:
    """Загружает сохранённые хэши с диска при старте."""
    try:
        if os.path.exists(_MOCK_FILE):
            with open(_MOCK_FILE, "r") as f:
                data = json.load(f)
                log.info("Mock registry loaded: %d hashes", len(data))
                return data
    except Exception as exc:
        log.warning("Cannot load mock registry: %s", exc)
    return {}


def _save_mock_registry(registry: dict):
    """Сохраняет хэши на диск после каждого store."""
    try:
        os.makedirs(Config.KEYS_DIR, exist_ok=True)
        with open(_MOCK_FILE, "w") as f:
            json.dump(registry, f, indent=2)
    except Exception as exc:
        log.warning("Cannot save mock registry: %s", exc)


# Загружаем хэши при старте приложения
_MOCK_REGISTRY: dict = _load_mock_registry()


# ─── Blockchain Client ────────────────────────────────────────────────────────
class BlockchainClient:
    """
    Web3 клиент для работы с Ganache.
    Если Ganache недоступен — работает в mock режиме
    с сохранением хэшей на диск (keys/mock_registry.json).
    """

    _instance = None

    def __init__(self):
        self.w3         = None
        self.contract   = None
        self.account    = None
        self._connected = False
        self._connect()

    @classmethod
    def get_instance(cls) -> "BlockchainClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Подключение к Ganache ─────────────────────────────────────────────────
    def _connect(self):
        try:
            self.w3 = Web3(Web3.HTTPProvider(
                Config.GANACHE_URL,
                request_kwargs={"timeout": 5}
            ))
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.w3.is_connected():
                raise ConnectionError(
                    f"Cannot reach Ganache at {Config.GANACHE_URL}"
                )

            self.account    = self.w3.eth.accounts[0]
            self._connected = True
            log.info("✅ Blockchain connected → %s  (account: %s)",
                     Config.GANACHE_URL, self.account)

        except Exception as exc:
            self._connected = False
            log.warning("⚠️  Blockchain offline: %s — running mock mode.", exc)

    # ── store_hash ────────────────────────────────────────────────────────────
    def store_hash(self, hex_hash: str) -> dict:
        """
        Сохранить SHA-256 хэш.
        Если Ganache доступен — пишем транзакцию.
        Иначе — сохраняем в mock_registry.json на диске.
        """
        if not self._connected:
            return self._do_mock_store(hex_hash)

        try:
            tx_hash = self.w3.eth.send_transaction({
                "from" : self.account,
                "to"   : self.account,
                "data" : "0x" + hex_hash,
                "gas"  : 100000,
            })
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

            # Дополнительно сохраняем в mock чтобы check_hash_exists работал
            _MOCK_REGISTRY[hex_hash] = time.time()
            _save_mock_registry(_MOCK_REGISTRY)

            result = {
                "tx_hash" : tx_hash.hex(),
                "block"   : receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "status"  : "success",
            }
            log.info("Hash stored on-chain → tx=%s  block=%d",
                     result["tx_hash"][:18], result["block"])
            return result

        except Exception as exc:
            log.warning("Ganache store failed, fallback to mock: %s", exc)
            return self._do_mock_store(hex_hash)

    # ── check_hash_exists ─────────────────────────────────────────────────────
    def check_hash_exists(self, hex_hash: str) -> dict:
        """
        Проверить наличие хэша.
        Ищем в mock_registry.json (работает и с Ganache и без него).
        """
        try:
            exists = hex_hash in _MOCK_REGISTRY
            ts     = _MOCK_REGISTRY.get(hex_hash, 0)

            log.debug("Hash check: exists=%s  hash=%s…", exists, hex_hash[:16])
            return {
                "exists"   : exists,
                "sender"   : self.account or "0x0000000000000000000000000000000000000000",
                "timestamp": int(ts),
            }
        except Exception as exc:
            log.error("check_hash_exists error: %s", exc)
            return {
                "exists"   : False,
                "sender"   : "",
                "timestamp": 0,
            }

    # ── get_total_hashes ──────────────────────────────────────────────────────
    def get_total_hashes(self) -> int:
        """Количество сохранённых хэшей."""
        return len(_MOCK_REGISTRY)

    # ── Mock методы ───────────────────────────────────────────────────────────
    def _do_mock_store(self, hex_hash: str) -> dict:
        """
        Сохранить хэш локально когда Ganache недоступен.
        Данные сохраняются в keys/mock_registry.json —
        не теряются при перезапуске сервера.
        """
        global _MOCK_REGISTRY
        _MOCK_REGISTRY[hex_hash] = time.time()
        _save_mock_registry(_MOCK_REGISTRY)   # ← сохраняем на диск

        fake_tx = "0xMOCK_" + hex_hash[:32]
        log.warning("MOCK store: hash=%s…  saved to disk ✅", hex_hash[:16])
        return {
            "tx_hash" : fake_tx,
            "block"   : 0,
            "gas_used": 0,
            "status"  : "mock",
        }


# ─── Singleton ────────────────────────────────────────────────────────────────
def get_blockchain() -> BlockchainClient:
    return BlockchainClient.get_instance()