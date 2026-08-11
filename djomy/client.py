"""Client pour l'API de paiement Djomy (https://developers.djomy.africa).

Flux utilisé : create_payment_gateway (portail hébergé par Djomy), qui délègue
le choix du moyen de paiement et la saisie de l'OTP au portail Djomy. Le
paiement doit ensuite être confirmé côté serveur via verify_payment (le retour
returnUrl / le webhook ne sont jamais une preuve suffisante de paiement).

Authentification : un jeton Bearer obtenu via POST /v1/auth, avec un en-tête
X-API-KEY: "{client_id}:{hex(HMAC-SHA256(clé=client_secret, message=client_id))}".
Ce même en-tête X-API-KEY doit accompagner chaque appel authentifié en plus du
jeton Bearer.
"""
import hashlib
import hmac

import requests
from django.conf import settings


class DjomyError(Exception):
    """Erreur retournée par l'API Djomy ou erreur réseau/transport."""

    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details


class DjomyClient:
    def __init__(self, client_id=None, client_secret=None, base_url=None, timeout=20):
        self.client_id = client_id or settings.DJOMY_CLIENT_ID
        self.client_secret = client_secret or settings.DJOMY_CLIENT_SECRET
        self.base_url = (base_url or settings.DJOMY_BASE_URL).rstrip('/')
        self.timeout = timeout

    def _signature(self):
        return hmac.new(
            self.client_secret.encode('utf-8'),
            self.client_id.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

    def _api_key_header(self):
        return f"{self.client_id}:{self._signature()}"

    def _get_access_token(self):
        response = requests.post(
            f"{self.base_url}/v1/auth",
            headers={'X-API-KEY': self._api_key_header()},
            json={},
            timeout=self.timeout,
        )
        payload = self._parse(response)
        token = (payload.get('data') or {}).get('accessToken')
        if not token:
            raise DjomyError("Réponse d'authentification Djomy sans accessToken.")
        return token

    def _parse(self, response):
        try:
            payload = response.json()
        except ValueError as exc:
            raise DjomyError(f"Réponse Djomy invalide (HTTP {response.status_code}).") from exc

        if not response.ok or not payload.get('success', response.ok):
            error = payload.get('error') or {}
            raise DjomyError(
                error.get('message') or payload.get('message') or "Erreur Djomy inconnue.",
                code=error.get('code', response.status_code),
                details=error.get('details'),
            )
        return payload

    def _authenticated_headers(self):
        return {
            'Authorization': f"Bearer {self._get_access_token()}",
            'X-API-KEY': self._api_key_header(),
        }

    def create_payment_gateway(self, amount, payer_number, country_code='GN', description=None,
                                merchant_payment_reference=None, return_url=None, cancel_url=None,
                                allowed_payment_methods=None, metadata=None):
        """Initie un paiement via le portail hébergé Djomy et renvoie data (transactionId, redirectUrl, ...)."""
        body = {
            'amount': amount,
            'countryCode': country_code,
            'payerNumber': payer_number,
        }
        if description:
            body['description'] = description
        if merchant_payment_reference:
            body['merchantPaymentReference'] = merchant_payment_reference
        if return_url:
            body['returnUrl'] = return_url
        if cancel_url:
            body['cancelUrl'] = cancel_url
        if allowed_payment_methods:
            body['allowedPaymentMethods'] = allowed_payment_methods
        if metadata:
            body['metadata'] = metadata

        response = requests.post(
            f"{self.base_url}/v1/payments/gateway",
            headers=self._authenticated_headers(),
            json=body,
            timeout=self.timeout,
        )
        return self._parse(response)['data']

    def verify_payment(self, transaction_id):
        """Interroge le statut réel d'une transaction. C'est la seule source de vérité."""
        response = requests.get(
            f"{self.base_url}/v1/payments/{transaction_id}/status",
            headers=self._authenticated_headers(),
            timeout=self.timeout,
        )
        return self._parse(response)['data']

    def verify_webhook_signature(self, raw_body, signature_header):
        """Vérifie l'en-tête X-Webhook-Signature ("v1:<hex>") d'un appel webhook entrant."""
        if not signature_header or ':' not in signature_header:
            return False
        version, _, received_hex = signature_header.partition(':')
        if version != 'v1':
            return False
        expected_hex = hmac.new(
            self.client_secret.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_hex, received_hex)
