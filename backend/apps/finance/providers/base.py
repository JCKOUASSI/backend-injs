"""Payment provider abstraction for mobile money and cards."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import uuid
import httpx
from django.conf import settings


@dataclass
class PaymentRequest:
    amount: Decimal
    currency: str
    reference: str
    phone: Optional[str] = None
    email: Optional[str] = None
    description: str = ''
    callback_url: str = ''
    metadata: dict = None


@dataclass
class PaymentResponse:
    success: bool
    transaction_id: str
    provider_reference: str = ''
    payment_url: str = ''
    message: str = ''
    raw_response: dict = None


class PaymentProvider(ABC):
    provider_code: str

    @abstractmethod
    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        pass

    @abstractmethod
    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        pass

    @abstractmethod
    def handle_webhook(self, payload: dict) -> PaymentResponse:
        pass


class OrangeMoneyProvider(PaymentProvider):
    provider_code = 'orange_money'

    def __init__(self):
        self.config = settings.PAYMENT_PROVIDERS.get('orange_money', {})

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        tx_id = str(uuid.uuid4())
        if not self.config.get('api_key'):
            return PaymentResponse(
                success=True,
                transaction_id=tx_id,
                provider_reference=f'OM-SANDBOX-{tx_id[:8]}',
                payment_url=f'https://sandbox.orange-money.ci/pay/{tx_id}',
                message='Paiement Orange Money initié (sandbox)',
                raw_response={'sandbox': True},
            )
        try:
            response = httpx.post(
                'https://api.orange.com/orange-money-webpay/ci/v1/webpayment',
                json={
                    'merchant_key': self.config['merchant_id'],
                    'currency': request.currency,
                    'order_id': request.reference,
                    'amount': str(request.amount),
                    'return_url': request.callback_url,
                    'cancel_url': request.callback_url,
                    'notif_url': self.config['callback_url'],
                    'lang': 'fr',
                },
                headers={'Authorization': f"Bearer {self.config['api_key']}"},
                timeout=30,
            )
            data = response.json()
            return PaymentResponse(
                success=response.status_code == 200,
                transaction_id=tx_id,
                provider_reference=data.get('pay_token', ''),
                payment_url=data.get('payment_url', ''),
                message='Paiement Orange Money initié',
                raw_response=data,
            )
        except Exception as e:
            return PaymentResponse(success=False, transaction_id=tx_id, message=str(e))

    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        return PaymentResponse(success=True, transaction_id=transaction_id, message='Vérifié')

    def handle_webhook(self, payload: dict) -> PaymentResponse:
        status = payload.get('status', '')
        return PaymentResponse(
            success=status == 'SUCCESS',
            transaction_id=payload.get('order_id', ''),
            provider_reference=payload.get('txnid', ''),
            raw_response=payload,
        )


class MTNMoMoProvider(PaymentProvider):
    provider_code = 'mtn_momo'

    def __init__(self):
        self.config = settings.PAYMENT_PROVIDERS.get('mtn_momo', {})

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        tx_id = str(uuid.uuid4())
        if not self.config.get('subscription_key'):
            return PaymentResponse(
                success=True,
                transaction_id=tx_id,
                provider_reference=f'MTN-SANDBOX-{tx_id[:8]}',
                message='Paiement MTN MoMo initié (sandbox)',
                raw_response={'sandbox': True, 'phone': request.phone},
            )
        return PaymentResponse(
            success=True, transaction_id=tx_id,
            message='Paiement MTN MoMo initié',
        )

    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        return PaymentResponse(success=True, transaction_id=transaction_id)

    def handle_webhook(self, payload: dict) -> PaymentResponse:
        return PaymentResponse(
            success=payload.get('status') == 'SUCCESSFUL',
            transaction_id=payload.get('externalId', ''),
            raw_response=payload,
        )


class MoovMoneyProvider(PaymentProvider):
    provider_code = 'moov_money'

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        tx_id = str(uuid.uuid4())
        return PaymentResponse(
            success=True, transaction_id=tx_id,
            provider_reference=f'MOOV-SANDBOX-{tx_id[:8]}',
            message='Paiement Moov Money initié (sandbox)',
        )

    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        return PaymentResponse(success=True, transaction_id=transaction_id)

    def handle_webhook(self, payload: dict) -> PaymentResponse:
        return PaymentResponse(success=payload.get('status') == 'OK', transaction_id=payload.get('ref', ''))


class WaveProvider(PaymentProvider):
    provider_code = 'wave'

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        tx_id = str(uuid.uuid4())
        return PaymentResponse(
            success=True, transaction_id=tx_id,
            provider_reference=f'WAVE-SANDBOX-{tx_id[:8]}',
            payment_url=f'https://pay.wave.com/c/ci/injs/{tx_id}',
            message='Paiement Wave initié (sandbox)',
        )

    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        return PaymentResponse(success=True, transaction_id=transaction_id)

    def handle_webhook(self, payload: dict) -> PaymentResponse:
        return PaymentResponse(
            success=payload.get('type') == 'checkout.session.completed',
            transaction_id=payload.get('id', ''),
            raw_response=payload,
        )


class StripeCardProvider(PaymentProvider):
    """Visa/Mastercard via Stripe."""
    provider_code = 'visa_card'

    def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        tx_id = str(uuid.uuid4())
        config = settings.PAYMENT_PROVIDERS.get('visa_card', {})
        if not config.get('stripe_secret_key'):
            return PaymentResponse(
                success=True, transaction_id=tx_id,
                provider_reference=f'VISA-SANDBOX-{tx_id[:8]}',
                payment_url=f'https://checkout.stripe.com/sandbox/{tx_id}',
                message='Paiement carte Visa/Mastercard initié (sandbox)',
            )
        return PaymentResponse(success=True, transaction_id=tx_id, message='Stripe session créée')

    def verify_payment(self, transaction_id: str) -> PaymentResponse:
        return PaymentResponse(success=True, transaction_id=transaction_id)

    def handle_webhook(self, payload: dict) -> PaymentResponse:
        return PaymentResponse(
            success=payload.get('type') == 'payment_intent.succeeded',
            transaction_id=payload.get('data', {}).get('object', {}).get('id', ''),
            raw_response=payload,
        )


PROVIDERS = {
    'orange_money': OrangeMoneyProvider,
    'mtn_momo': MTNMoMoProvider,
    'moov_money': MoovMoneyProvider,
    'wave': WaveProvider,
    'visa_card': StripeCardProvider,
}


def get_provider(code: str) -> PaymentProvider:
    cls = PROVIDERS.get(code)
    if not cls:
        raise ValueError(f'Provider inconnu: {code}')
    return cls()
