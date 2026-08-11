import hashlib
import hmac
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tenants.models import Entreprise

from .client import DjomyClient, DjomyError
from .models import PaiementAbonnement
from .utils import ajouter_mois
from .views import _appliquer_resultat

DJOMY_SETTINGS = dict(
    DJOMY_CLIENT_ID='test-client-id',
    DJOMY_CLIENT_SECRET='test-client-secret',
    DJOMY_BASE_URL='https://sandbox-api.djomy.africa',
)


def _fake_response(payload, status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.json.return_value = payload
    return resp


@override_settings(**DJOMY_SETTINGS)
class DjomyClientTests(TestCase):
    def test_signature_is_hmac_secret_key_client_id_message(self):
        client = DjomyClient()
        expected = hmac.new(b'test-client-secret', b'test-client-id', hashlib.sha256).hexdigest()
        self.assertEqual(client._signature(), expected)
        self.assertEqual(client._api_key_header(), f"test-client-id:{expected}")

    @patch('djomy.client.requests.post')
    def test_create_payment_gateway_returns_data(self, mock_post):
        mock_post.side_effect = [
            _fake_response({'success': True, 'data': {'accessToken': 'tok123'}}),
            _fake_response({'success': True, 'data': {
                'transactionId': 'txn-1', 'status': 'REDIRECTED',
                'redirectUrl': 'https://sandbox-portal.djomy.africa/pay/txn-1',
            }}),
        ]
        data = DjomyClient().create_payment_gateway(
            amount=150000, payer_number='00224623707722', country_code='GN',
            merchant_payment_reference='ABN-1-abc',
        )
        self.assertEqual(data['transactionId'], 'txn-1')
        self.assertEqual(data['status'], 'REDIRECTED')

        auth_call, gateway_call = mock_post.call_args_list
        self.assertTrue(auth_call.args[0].endswith('/v1/auth'))
        self.assertTrue(gateway_call.args[0].endswith('/v1/payments/gateway'))
        self.assertEqual(gateway_call.kwargs['headers']['Authorization'], 'Bearer tok123')
        self.assertIn('X-API-KEY', gateway_call.kwargs['headers'])
        self.assertEqual(gateway_call.kwargs['json']['merchantPaymentReference'], 'ABN-1-abc')

    @patch('djomy.client.requests.post')
    def test_create_payment_gateway_raises_djomy_error_on_failure(self, mock_post):
        mock_post.side_effect = [
            _fake_response({'success': True, 'data': {'accessToken': 'tok123'}}),
            _fake_response(
                {'success': False, 'error': {'code': 400, 'message': 'Le numéro de téléphone est obligatoire.'}},
                status_code=400,
            ),
        ]
        with self.assertRaises(DjomyError):
            DjomyClient().create_payment_gateway(amount=150000, payer_number='', country_code='GN')

    @patch('djomy.client.requests.get')
    @patch('djomy.client.requests.post')
    def test_verify_payment(self, mock_post, mock_get):
        mock_post.return_value = _fake_response({'success': True, 'data': {'accessToken': 'tok123'}})
        mock_get.return_value = _fake_response({'success': True, 'data': {
            'transactionId': 'txn-1', 'status': 'SUCCESS', 'paidAmount': 150000,
        }})
        data = DjomyClient().verify_payment('txn-1')
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertTrue(mock_get.call_args.args[0].endswith('/v1/payments/txn-1/status'))

    def test_verify_webhook_signature(self):
        client = DjomyClient()
        raw_body = b'{"eventType":"payment.success"}'
        digest = hmac.new(b'test-client-secret', raw_body, hashlib.sha256).hexdigest()
        self.assertTrue(client.verify_webhook_signature(raw_body, f"v1:{digest}"))
        self.assertFalse(client.verify_webhook_signature(raw_body, f"v1:{'0' * 64}"))
        self.assertFalse(client.verify_webhook_signature(raw_body, f"v2:{digest}"))
        self.assertFalse(client.verify_webhook_signature(raw_body, ''))


class AjouterMoisTests(TestCase):
    def test_ajoute_mois_simple(self):
        import datetime
        self.assertEqual(ajouter_mois(datetime.date(2026, 1, 15), 1), datetime.date(2026, 2, 15))

    def test_ajoute_mois_change_annee(self):
        import datetime
        self.assertEqual(ajouter_mois(datetime.date(2026, 12, 1), 3), datetime.date(2027, 3, 1))

    def test_borne_fin_de_mois(self):
        import datetime
        self.assertEqual(ajouter_mois(datetime.date(2026, 1, 31), 1), datetime.date(2026, 2, 28))


@override_settings(**DJOMY_SETTINGS)
class AppliquerResultatTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        self.paiement = PaiementAbonnement.all_objects.create(
            entreprise=self.entreprise, duree_mois=3, montant=450000,
            payer_number='00224623707722', merchant_reference='ABN-1-abc',
            statut='REDIRECTED', transaction_id='txn-1',
        )

    def test_success_extends_contract_from_today_when_no_prior_contract(self):
        aujourdhui = timezone.localdate()
        _appliquer_resultat('ABN-1-abc', {'status': 'SUCCESS', 'transactionId': 'txn-1'})
        self.entreprise.refresh_from_db()
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, 'SUCCESS')
        self.assertEqual(self.entreprise.date_fin_contrat, ajouter_mois(aujourdhui, 3))

    def test_success_extends_from_existing_future_end_date(self):
        import datetime
        future = timezone.localdate() + datetime.timedelta(days=10)
        self.entreprise.date_fin_contrat = future
        self.entreprise.save()
        _appliquer_resultat('ABN-1-abc', {'status': 'SUCCESS', 'transactionId': 'txn-1'})
        self.entreprise.refresh_from_db()
        self.assertEqual(self.entreprise.date_fin_contrat, ajouter_mois(future, 3))

    def test_success_is_idempotent_does_not_double_extend(self):
        _appliquer_resultat('ABN-1-abc', {'status': 'SUCCESS', 'transactionId': 'txn-1'})
        self.entreprise.refresh_from_db()
        premiere_date = self.entreprise.date_fin_contrat

        _appliquer_resultat('ABN-1-abc', {'status': 'SUCCESS', 'transactionId': 'txn-1'})
        self.entreprise.refresh_from_db()
        self.assertEqual(self.entreprise.date_fin_contrat, premiere_date)

    def test_failed_status_does_not_touch_contract(self):
        _appliquer_resultat('ABN-1-abc', {'status': 'FAILED', 'transactionId': 'txn-1'})
        self.entreprise.refresh_from_db()
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, 'FAILED')
        self.assertIsNone(self.entreprise.date_fin_contrat)

    def test_unknown_reference_returns_none(self):
        self.assertIsNone(_appliquer_resultat('inconnue', {'status': 'SUCCESS'}))


@override_settings(**DJOMY_SETTINGS)
class WebhookViewTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        self.paiement = PaiementAbonnement.all_objects.create(
            entreprise=self.entreprise, duree_mois=1, montant=150000,
            payer_number='00224623707722', merchant_reference='ABN-1-xyz',
            statut='REDIRECTED', transaction_id='txn-2',
        )

    def _sign(self, body):
        digest = hmac.new(b'test-client-secret', body, hashlib.sha256).hexdigest()
        return f"v1:{digest}"

    def test_rejects_invalid_signature(self):
        body = json.dumps({'eventType': 'payment.success'}).encode()
        response = self.client.post(
            reverse('djomy_webhook'), data=body, content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE='v1:deadbeef',
        )
        self.assertEqual(response.status_code, 403)

    @patch('djomy.client.requests.get')
    @patch('djomy.client.requests.post')
    def test_success_event_confirms_and_extends_contract(self, mock_post, mock_get):
        mock_post.return_value = _fake_response({'success': True, 'data': {'accessToken': 'tok'}})
        mock_get.return_value = _fake_response({'success': True, 'data': {
            'transactionId': 'txn-2', 'status': 'SUCCESS',
            'merchantPaymentReference': 'ABN-1-xyz',
        }})

        payload = {
            'eventType': 'payment.success',
            'data': {'transactionId': 'txn-2', 'merchantPaymentReference': 'ABN-1-xyz'},
        }
        body = json.dumps(payload).encode()
        response = self.client.post(
            reverse('djomy_webhook'), data=body, content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=self._sign(body),
        )
        self.assertEqual(response.status_code, 200)
        self.paiement.refresh_from_db()
        self.entreprise.refresh_from_db()
        self.assertEqual(self.paiement.statut, 'SUCCESS')
        self.assertIsNotNone(self.entreprise.date_fin_contrat)


@override_settings(**DJOMY_SETTINGS)
class RenouvelerAbonnementViewTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        User = get_user_model()
        self.user = User.objects.create_user(username='proprio', password='pass1234')
        self.user.entreprise = self.entreprise
        self.user.save()
        self.client.login(username='proprio', password='pass1234')

    @patch('djomy.client.requests.post')
    def test_get_renders_form(self, mock_post):
        response = self.client.get(reverse('djomy_renouveler'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Renouveler')

    @patch('djomy.client.requests.post')
    def test_post_redirects_to_djomy_portal(self, mock_post):
        mock_post.side_effect = [
            _fake_response({'success': True, 'data': {'accessToken': 'tok'}}),
            _fake_response({'success': True, 'data': {
                'transactionId': 'txn-3', 'status': 'REDIRECTED',
                'redirectUrl': 'https://sandbox-portal.djomy.africa/pay/txn-3',
            }}),
        ]
        response = self.client.post(reverse('djomy_renouveler'), {
            'duree_mois': '3', 'payer_number': '00224623707722',
        })
        self.assertRedirects(response, 'https://sandbox-portal.djomy.africa/pay/txn-3', fetch_redirect_response=False)
        paiement = PaiementAbonnement.all_objects.get(entreprise=self.entreprise)
        self.assertEqual(paiement.duree_mois, 3)
        self.assertEqual(paiement.montant, 3 * 150000)
        self.assertEqual(paiement.transaction_id, 'txn-3')

    @patch('djomy.client.requests.post')
    def test_post_shows_error_on_djomy_failure(self, mock_post):
        mock_post.side_effect = [
            _fake_response({'success': True, 'data': {'accessToken': 'tok'}}),
            _fake_response({'success': False, 'error': {'message': 'Erreur sandbox'}}, status_code=400),
        ]
        response = self.client.post(reverse('djomy_renouveler'), {
            'duree_mois': '1', 'payer_number': '00224623707722',
        })
        self.assertEqual(response.status_code, 200)
        paiement = PaiementAbonnement.all_objects.get(entreprise=self.entreprise)
        self.assertEqual(paiement.statut, 'FAILED')

    @patch('djomy.client.requests.post')
    def test_renouveler_accessible_meme_si_contrat_pas_proche_de_lexpiration(self, mock_post):
        import datetime
        self.entreprise.date_fin_contrat = timezone.localdate() + datetime.timedelta(days=200)
        self.entreprise.save()

        mock_post.side_effect = [
            _fake_response({'success': True, 'data': {'accessToken': 'tok'}}),
            _fake_response({'success': True, 'data': {
                'transactionId': 'txn-4', 'status': 'REDIRECTED',
                'redirectUrl': 'https://sandbox-portal.djomy.africa/pay/txn-4',
            }}),
        ]
        response = self.client.post(reverse('djomy_renouveler'), {
            'duree_mois': '12', 'payer_number': '00224623707722',
        })
        self.assertRedirects(response, 'https://sandbox-portal.djomy.africa/pay/txn-4', fetch_redirect_response=False)


@override_settings(**DJOMY_SETTINGS)
class HistoriquePaiementsViewTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        User = get_user_model()
        self.user = User.objects.create_user(username='proprio', password='pass1234')
        self.user.entreprise = self.entreprise
        self.user.save()
        self.client.login(username='proprio', password='pass1234')

    def test_liste_les_paiements_de_lentreprise(self):
        PaiementAbonnement.all_objects.create(
            entreprise=self.entreprise, duree_mois=1, montant=150000,
            payer_number='00224623707722', merchant_reference='ABN-1-a', statut='SUCCESS',
        )
        autre_entreprise = Entreprise.objects.create(nom="Autre boutique", ville="Kankan")
        PaiementAbonnement.all_objects.create(
            entreprise=autre_entreprise, duree_mois=1, montant=150000,
            payer_number='00224600000000', merchant_reference='ABN-2-b', statut='SUCCESS',
        )

        response = self.client.get(reverse('djomy_historique'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ABN-1-a')
        self.assertNotContains(response, 'ABN-2-b')
