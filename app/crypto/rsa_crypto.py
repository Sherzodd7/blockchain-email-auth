# app/crypto/rsa_crypto.py  — uses 'cryptography' library (pre-installed)
import os, base64, hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from config import Config
from app.utils.logger import log

def generate_keys():
    os.makedirs(Config.KEYS_DIR, exist_ok=True)
    priv = rsa.generate_private_key(65537, Config.RSA_KEY_SIZE, default_backend())
    priv_pem = priv.private_bytes(serialization.Encoding.PEM,
                                   serialization.PrivateFormat.PKCS8,
                                   serialization.NoEncryption()).decode()
    pub_pem  = priv.public_key().public_bytes(serialization.Encoding.PEM,
                                              serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    open(Config.PRIVATE_KEY_PATH, 'w').write(priv_pem)
    open(Config.PUBLIC_KEY_PATH,  'w').write(pub_pem)
    log.info("RSA-%d keys generated → %s", Config.RSA_KEY_SIZE, Config.KEYS_DIR)
    return priv_pem, pub_pem

def _load_priv():
    if not os.path.exists(Config.PRIVATE_KEY_PATH): generate_keys()
    return serialization.load_pem_private_key(open(Config.PRIVATE_KEY_PATH,'rb').read(), None, default_backend())

def _load_pub():
    if not os.path.exists(Config.PUBLIC_KEY_PATH): generate_keys()
    return serialization.load_pem_public_key(open(Config.PUBLIC_KEY_PATH,'rb').read(), default_backend())

def get_public_key_pem():
    return _load_pub().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

def hash_message(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()

def sign_message(message: str) -> str:
    sig = _load_priv().sign(
        message.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    return base64.b64encode(sig).decode()

def verify_signature(message: str, sig_b64: str, public_key_pem=None) -> bool:
    try:
        if not sig_b64: return False
        pub = (serialization.load_pem_public_key(public_key_pem.encode(), default_backend())
               if public_key_pem else _load_pub())
        pub.verify(base64.b64decode(sig_b64), message.encode(),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                   hashes.SHA256())
        return True
    except (InvalidSignature, Exception):
        return False
    