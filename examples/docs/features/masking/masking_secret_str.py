"""SecretStr & PaymentCardNumber — mask sensitive values in str() and repr()."""

from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, load
from dature.fields.payment_card import PaymentCardNumber
from dature.fields.secret_str import SecretStr

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Config:
    api_key: SecretStr
    password: str
    host: str
    card_number: PaymentCardNumber
    metadata: str


config = load(LoadMetadata(file_=SOURCES_DIR / "masking_secrets.yaml"), Config)

assert str(config.api_key) == "**********"
assert config.api_key.get_secret_value() == "sk-proj-abc123def456"
assert config.host == "api.example.com"
assert str(config.password) == "**********"
assert str(config.card_number) == "************1111"
assert config.card_number.brand == "Visa"
assert config.metadata == "aK9$mP2xL5vQ8wR3nJ7yB4zT6"
