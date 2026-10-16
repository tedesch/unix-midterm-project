from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

def Create_Certification_file() -> Path:
    cert_dir = Path(__file__).resolve().parent.parent / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir

def get_cert_directory() -> Path:
    return Create_Certification_file()

def generate_key(cert_dir: str | Path | None = None):
    cert_dir = Path(cert_dir) if cert_dir is not None else get_cert_directory()
    cert_dir.mkdir(parents=True, exist_ok=True)

    key_path = cert_dir / "key.pem"
    cert_path = cert_dir / "cert.pem"

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Group 17"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Master Dashboard"),
    ])
    now = datetime.now(timezone.utc)

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("0.0.0.0")),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

    return private_key, certificate


def load_key():
    key_path = get_cert_directory() / "key.pem"
    if not key_path.exists():
        generate_key()
    with key_path.open("rb") as key_file:
        return serialization.load_pem_private_key(key_file.read(), password=None)


def get_ssl_context():
    cert_dir = get_cert_directory()
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"
    if not cert_path.exists() or not key_path.exists():
        generate_key(cert_dir)
    return str(cert_path), str(key_path)
