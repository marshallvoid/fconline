from enum import Enum


class PaymentType(Enum):
    FC = 1
    MC = 2

    @property
    def text(self) -> str:
        return "FC" if self == PaymentType.FC else "MC"

    @staticmethod
    def from_text(text: str) -> "PaymentType":
        return PaymentType.FC if text == "FC" else PaymentType.MC

    @staticmethod
    def from_int(value: int) -> "PaymentType":
        return PaymentType.FC if value == 1 else PaymentType.MC
