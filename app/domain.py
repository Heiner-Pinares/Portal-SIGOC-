from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ServiceRecord:
    plan: str
    plan_name: str
    campaign: str
    campaign_name: str
    solution: str
    tmcode: Optional[str]
    spcode: Optional[str]
    sncode: str
    service: Optional[str]
    service_name: str
    charge_without_tax: Decimal
    charge_with_tax: Decimal
    service_type: str
    key: str

    def to_dict(self):
        data = asdict(self)
        data["charge_without_tax"] = f"{self.charge_without_tax:.2f}"
        data["charge_with_tax"] = f"{self.charge_with_tax:.2f}"
        return data

