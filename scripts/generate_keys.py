from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
AUTH_DIR = BACKEND_DIR / "auth"


def main() -> None:
    services = [directory for directory in BACKEND_DIR.iterdir() if directory.is_dir()]

    if not AUTH_DIR.exists():
        raise FileNotFoundError("backend/auth/ directory not found.")

    auth_keys_dir = AUTH_DIR / "keys"
    auth_keys_dir.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    private_key_path = auth_keys_dir / "private_key.pem"
    public_key = private_key.public_key()

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    print("[OK] Generated auth/private_key.pem")

    # Generate public_key.pem for every service.
    for service in services:
        keys_dir = service / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)

        public_key_path = keys_dir / "public_key.pem"

        public_key_path.write_bytes(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        print(f"[OK] Generated {service.name}/keys/public_key.pem")


if __name__ == "__main__":
    main()
