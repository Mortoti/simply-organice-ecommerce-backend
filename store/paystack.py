import requests
import hmac
import hashlib
from django.conf import settings
from decimal import Decimal


class PaystackAPI:
    """
    Utility class for handling Paystack payment operations.
    All amounts are in pesewas (GHS * 100) as required by Paystack.
    """

    BASE_URL = "https://api.paystack.co"

    @staticmethod
    def _get_headers():
        """Returns the authorization headers for Paystack API requests."""
        return {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

    @staticmethod
    def _convert_to_pesewas(amount):
        """
        Convert GHS amount to pesewas (smallest currency unit).
        Paystack requires amounts in pesewas (1 GHS = 100 pesewas).

        Args:
            amount: Decimal or float amount in GHS

        Returns:
            int: Amount in pesewas
        """
        return int(Decimal(str(amount)) * 100)

    @classmethod
    def initialize_payment(cls, email, amount, order_id, callback_url=None):
        """
        Initialize a payment transaction with Paystack.

        Args:
            email (str): Customer's email address
            amount (Decimal): Amount to charge in GHS
            order_id (int): Your order ID for reference
            callback_url (str, optional): URL to redirect after payment

        Returns:
            dict: {
                'status': bool,
                'message': str,
                'data': dict or None (contains authorization_url, access_code, reference)
            }
        """
        url = f"{cls.BASE_URL}/transaction/initialize"

        # Prepare the payload
        payload = {
            "email": email,
            "amount": cls._convert_to_pesewas(amount),  # Convert to pesewas
            "currency": "GHS",
            "metadata": {
                "order_id": order_id,
                "custom_fields": [
                    {
                        "display_name": "Order ID",
                        "variable_name": "order_id",
                        "value": order_id
                    }
                ]
            }
        }

        # Add callback URL if provided
        if callback_url:
            payload['callback_url'] = callback_url

        try:
            response = requests.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=10
            )

            response_data = response.json()

            if response.status_code == 200 and response_data.get('status'):
                return {
                    'status': True,
                    'message': 'Payment initialized successfully',
                    'data': response_data.get('data')
                }
            else:
                return {
                    'status': False,
                    'message': response_data.get('message', 'Failed to initialize payment'),
                    'data': None
                }

        except requests.exceptions.Timeout:
            return {
                'status': False,
                'message': 'Request timeout. Please try again.',
                'data': None
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': f'Network error: {str(e)}',
                'data': None
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'An error occurred: {str(e)}',
                'data': None
            }

    @classmethod
    def verify_payment(cls, reference):
        """
        Verify a payment transaction with Paystack.

        Args:
            reference (str): The payment reference to verify

        Returns:
            dict: {
                'status': bool,
                'message': str,
                'data': dict or None (contains transaction details)
            }
        """
        url = f"{cls.BASE_URL}/transaction/verify/{reference}"

        try:
            response = requests.get(
                url,
                headers=cls._get_headers(),
                timeout=10
            )

            response_data = response.json()

            if response.status_code == 200 and response_data.get('status'):
                transaction_data = response_data.get('data', {})

                # Check if payment was actually successful
                if transaction_data.get('status') == 'success':
                    return {
                        'status': True,
                        'message': 'Payment verified successfully',
                        'data': transaction_data
                    }
                else:
                    return {
                        'status': False,
                        'message': f"Payment status: {transaction_data.get('status')}",
                        'data': transaction_data
                    }
            else:
                return {
                    'status': False,
                    'message': response_data.get('message', 'Failed to verify payment'),
                    'data': None
                }

        except requests.exceptions.Timeout:
            return {
                'status': False,
                'message': 'Request timeout. Please try again.',
                'data': None
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': f'Network error: {str(e)}',
                'data': None
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'An error occurred: {str(e)}',
                'data': None
            }

    @staticmethod
    def verify_webhook_signature(payload, signature):
        """
        Verify that a webhook request actually came from Paystack.
        This is critical for security!

        Args:
            payload (bytes): Raw request body
            signature (str): X-Paystack-Signature header value

        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Create HMAC hash of the payload using your secret key
            hash_object = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
                payload,
                hashlib.sha512
            )
            expected_signature = hash_object.hexdigest()

            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            print(f"Webhook signature verification error: {e}")
            return False