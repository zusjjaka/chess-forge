from pathlib import Path

from core.config import get_settings

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_DIR = BASE_DIR / 'keys'

PRIVATE_KEY = (KEYS_DIR / 'private_key.pem').read_text()
PUBLIC_KEY = (KEYS_DIR / 'public_key.pem').read_text()
