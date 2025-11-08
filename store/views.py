from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import hmac
import hashlib
from decimal import Decimal
from .paystack import PaystackAPI

from .models import Product, Collection, Cart, CartItem, Customer, Order, ProductImage

from .serializers import ProductSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, \
    AddCartItemSerializer, UpdateCartItemSerializer, CustomerSerializer, OrderSerializer, CreateOrderSerializer, \
    UpdateOrderSerializer, ProductImageSerializer

from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly, ViewCustomerHistoryPermissions

from .pagination import DefaultPagination


# Create your views here.
class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.prefetch_related('images').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'description']
    ordering_fields = ['price']
    pagination_class = DefaultPagination


class ProductImageViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer

    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}

    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs['product_pk'])


class CollectionViewSet(ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return Collection.objects.prefetch_related('products').annotate(
                product_count=Count('products'))
        return queryset


class CartViewSet(GenericViewSet, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        else:
            return CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk']).select_related('product')

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, permission_classes=[ViewCustomerHistoryPermissions])
    def history(self, request, pk):
        return Response("OK")

    @action(detail=False, methods=['GET', 'PUT'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = Customer.objects.get(user_id=request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'user_id': self.request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        elif self.request.method == 'PATCH':
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        customer_id = Customer.objects.only('id').get(user_id=user.id)
        return Order.objects.filter(customer_id=customer_id)


class VerifyPaymentView(APIView):
    """
    Verify a Paystack payment transaction.

    GET /api/payments/verify/?reference=<payment_reference>

    This is called after the user completes payment on Paystack.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get the payment reference from query parameters
        reference = request.query_params.get('reference', None)

        if not reference:
            return Response(
                {"error": "Payment reference is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the payment with Paystack
        result = PaystackAPI.verify_payment(reference)

        if not result['status']:
            return Response(
                {"error": result['message']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Payment verification successful
        payment_data = result['data']

        # Get order ID from metadata
        order_id = payment_data.get('metadata', {}).get('order_id', None)

        if not order_id:
            return Response(
                {"error": "Order ID not found in transaction metadata."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify the order belongs to the current user (security check)
        try:
            customer = Customer.objects.get(user_id=request.user.id)
            if order.customer != customer:
                return Response(
                    {"error": "You don't have permission to access this order."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get payment status from Paystack
        payment_status = payment_data.get('status')
        amount = float(payment_data.get('amount', 0)) / 100  # Convert from pesewas
        currency = payment_data.get('currency', 'GHS')
        paid_at = payment_data.get('paid_at')

        # Handle different payment statuses
        if payment_status == 'success':
            # Check if already marked as completed
            if order.payment_status == Order.PAYMENT_COMPLETED:
                return Response(
                    {
                        "message": "Payment already confirmed.",
                        "order_id": order.id,
                        "amount": amount,
                        "currency": currency,
                        "paid_at": paid_at
                    },
                    status=status.HTTP_200_OK
                )

            # Update order to completed only if it's still pending
            if order.payment_status == Order.PAYMENT_PENDING:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    if order.payment_status == Order.PAYMENT_PENDING:
                        order.payment_status = Order.PAYMENT_COMPLETED
                        order.paystack_ref = reference
                        order.save()

                return Response(
                    {
                        "message": "Payment verified successfully and order updated.",
                        "order_id": order.id,
                        "reference": reference,
                        "amount": amount,
                        "currency": currency,
                        "paid_at": paid_at
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # Order was already processed (maybe by webhook)
                return Response(
                    {
                        "message": f"Payment status is {order.payment_status}",
                        "order_id": order.id,
                        "amount": amount,
                        "currency": currency
                    },
                    status=status.HTTP_200_OK
                )

        elif payment_status == 'failed':
            # Update order to failed if it's still pending
            if order.payment_status == Order.PAYMENT_PENDING:
                order.payment_status = Order.PAYMENT_FAILED
                order.paystack_ref = reference
                order.save()

            return Response(
                {
                    "error": "Payment verification failed.",
                    "order_id": order.id,
                    "status": payment_status,
                    "gateway_response": payment_data.get('gateway_response', 'Payment was not successful')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        else:

            return Response(
                {
                    "error": f"Payment status is {payment_status}",
                    "order_id": order.id,
                    "status": payment_status,
                    "message": payment_data.get('gateway_response', 'Payment could not be completed')
                },
                status=status.HTTP_400_BAD_REQUEST
            )
class InitializePaymentView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            # Get the order
            order = Order.objects.prefetch_related('items__product').get(id=order_id)

            # Verify the order belongs to the current user (security check)
            customer = Customer.objects.get(user_id=request.user.id)
            if order.customer != customer:
                return Response(
                    {"error": "You don't have permission to access this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if order is already paid
            if order.payment_status == Order.PAYMENT_COMPLETED:
                return Response(
                    {"error": "This order has already been paid."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate total amount from order items
            total_amount = sum(
                item.price_at_purchase * item.quantity
                for item in order.items.all()
            )

            if total_amount <= 0:
                return Response(
                    {"error": "Order total must be greater than zero."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get customer email
            customer_email = request.user.email

            if not customer_email:
                return Response(
                    {"error": "Customer email is required for payment."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Optional: Set callback URL (where Paystack redirects after payment)
            # You can customize this based on your frontend URL
            callback_url = request.data.get('callback_url', None)

            # Initialize payment with Paystack
            result = PaystackAPI.initialize_payment(
                email=customer_email,
                amount=total_amount,
                order_id=order.id,
                callback_url=callback_url
            )

            if result['status']:
                # Save the access code and reference to the order
                payment_data = result['data']
                order.paystack_ref = payment_data['reference']
                order.paystack_access_code = payment_data['access_code']
                order.save()

                return Response({
                    "message": "Payment initialized successfully",
                    "authorization_url": payment_data['authorization_url'],
                    "access_code": payment_data['access_code'],
                    "reference": payment_data['reference'],
                    "amount": float(total_amount),
                    "currency": "GHS"
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": result['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


import json
from django.db import transaction


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(APIView):
    """
    Handle webhook notifications from Paystack.

    POST /api/payments/webhook/

    This endpoint receives automatic notifications from Paystack
    when payment events occur (successful payment, failed payment, etc.)

    IMPORTANT: This endpoint is called by Paystack, not by your frontend!
    """
    permission_classes = []  # No authentication required for webhooks

    def post(self, request, *args, **kwargs):
        # Get the signature from headers
        signature = request.headers.get('X-Paystack-Signature', '')

        if not signature:
            return Response(
                {"error": "No signature provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get raw request body (needed for signature verification)
        payload = request.body

        # Verify the webhook signature
        if not PaystackAPI.verify_webhook_signature(payload, signature):
            return Response(
                {"error": "Invalid signature"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse the webhook data
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the event type
        event = webhook_data.get('event')

        # Handle charge.success event
        if event == 'charge.success':
            return self._handle_successful_payment(webhook_data)

        # Handle charge.failed event (optional but recommended)
        elif event == 'charge.failed':
            return self._handle_failed_payment(webhook_data)

        # For other events, just acknowledge receipt
        return Response({"status": "received"}, status=status.HTTP_200_OK)

    def _handle_successful_payment(self, webhook_data):
        """Handle successful payment webhook"""
        data = webhook_data.get('data', {})

        # Get order ID from metadata
        order_id = data.get('metadata', {}).get('order_id')

        if not order_id:
            # Log this for debugging but return 200 so Paystack doesn't retry
            print("Webhook received but no order_id in metadata")
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        # Get the payment reference and status
        reference = data.get('reference')
        payment_status = data.get('status')

        if not reference:
            print("Webhook received but no reference")
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        try:
            # Use select_for_update to prevent race conditions
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

                # Only update if payment is still pending
                if order.payment_status == Order.PAYMENT_PENDING:
                    if payment_status == 'success':
                        order.payment_status = Order.PAYMENT_COMPLETED
                        order.paystack_ref = reference
                        order.save()

                        print(f"✅ Order {order_id} payment confirmed via webhook")
                    else:
                        # Status is not 'success' even in charge.success event
                        order.payment_status = Order.PAYMENT_FAILED
                        order.paystack_ref = reference
                        order.save()

                        print(f"⚠️ Order {order_id} marked as failed (unexpected status in charge.success)")
                else:
                    # Order already processed (probably by VerifyPaymentView)
                    print(f"ℹ️ Order {order_id} already processed. Current status: {order.payment_status}")

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            print(f"❌ Webhook received for non-existent order: {order_id}")
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Error processing webhook for order {order_id}: {str(e)}")
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_failed_payment(self, webhook_data):
        """Handle failed payment webhook"""
        data = webhook_data.get('data', {})

        order_id = data.get('metadata', {}).get('order_id')
        reference = data.get('reference')

        if not order_id or not reference:
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

                # Only update if payment is still pending
                if order.payment_status == Order.PAYMENT_PENDING:
                    order.payment_status = Order.PAYMENT_FAILED
                    order.paystack_ref = reference
                    order.save()

                    print(f"Order {order_id} payment failed via webhook")

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            print(f"Webhook received for non-existent order: {order_id}")
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error processing failed payment webhook: {str(e)}")
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)