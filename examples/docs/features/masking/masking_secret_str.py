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
    card_number: PaymentCardNumber


config = load(LoadMetadata(file_=SOURCES_DIR / "masking_secret_str.yaml"), Config)

assert str(config.api_key) == "**********"
assert config.api_key.get_secret_value() == "sk-proj-abc123def456"
assert str(config.card_number) == "************1111"
assert config.card_number.brand == "Visa"
assert config.card_number.get_raw_number() == "4111111111111111"
