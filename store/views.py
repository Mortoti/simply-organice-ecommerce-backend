from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import RetrieveModelMixin, CreateModelMixin, DestroyModelMixin, ListModelMixin
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

from .models import Product, Collection, Cart, CartItem, Customer, Order, ProductImage, Branch

from .serializers import ProductSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, \
    AddCartItemSerializer, UpdateCartItemSerializer, CustomerSerializer, OrderSerializer, CreateOrderSerializer, \
    UpdateOrderSerializer, ProductImageSerializer, BranchSerializer

from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly, ViewCustomerHistoryPermissions

from .pagination import DefaultPagination


class BranchViewSet(ReadOnlyModelViewSet):
    serializer_class = BranchSerializer

    def get_queryset(self):
        return Branch.objects.filter(is_active=True)


class ProductViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'description']
    ordering_fields = ['price']
    pagination_class = DefaultPagination

    def get_queryset(self):
        queryset = Product.objects.select_related('collection').prefetch_related('images', 'sizes')

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_available=True)

        return queryset
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


class CartViewSet(ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related('items__product')

    def create(self, request, *args, **kwargs):
        existing_cart = Cart.objects.filter(user=request.user).first()

        if existing_cart:
            serializer = self.get_serializer(existing_cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

        cart = Cart.objects.create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        else:
            return CartItemSerializer

    def get_queryset(self):
        cart_id = self.kwargs['cart_pk']
        if not Cart.objects.filter(id=cart_id, user=self.request.user).exists():
            return CartItem.objects.none()

        return CartItem.objects.filter(cart_id=cart_id).select_related('product')

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}

    def create(self, request, *args, **kwargs):
        print("=" * 50)
        print("📥 RECEIVED REQUEST DATA:", request.data)
        print("=" * 50)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        print("✅ VALIDATED DATA:", serializer.validated_data)

        self.perform_create(serializer)

        cart_item = serializer.instance
        print("=" * 50)
        print("✅ CART ITEM CREATED IN DATABASE:")
        print(f"   ID: {cart_item.id}")
        print(f"   Product: {cart_item.product.name}")
        print(f"   Quantity: {cart_item.quantity}")
        print(f"   with_customization: {cart_item.with_customization}")
        print(f"   selected_size: {cart_item.selected_size}")
        print(f"   Product base price: {cart_item.product.price}")
        print(f"   Product customization price: {cart_item.product.customization_price}")
        print(f"   Product is_customizable: {cart_item.product.is_customizable}")

        calculated_total = cart_item.quantity * cart_item.product.price
        if cart_item.with_customization and cart_item.product.is_customizable:
            calculated_total += (cart_item.product.customization_price * cart_item.quantity)
        print(f"   CALCULATED TOTAL: {calculated_total}")
        print("=" * 50)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        elif self.request.method == 'PATCH':
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.prefetch_related('items__product').all()

        try:
            customer_id = Customer.objects.only('id').get(user_id=user.id)
            return Order.objects.prefetch_related('items__product').filter(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Order.objects.none()


from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    summary="Verify a Paystack payment transaction",
    description="Verify if a payment was successful after the user completes payment on Paystack.",
    parameters=[
        OpenApiParameter(
            name='reference',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='The payment reference returned by Paystack during initialization'
        ),
    ],
    responses={
        200: {
            'description': 'Payment verified successfully',
            'example': {
                "message": "Payment verified successfully and order updated.",
                "order_id": 1,
                "reference": "huqivva3ug",
                "amount": 645.0,
                "currency": "GHS",
                "paid_at": "2025-11-08T11:20:06.000Z"
            }
        },
        400: {
            'description': 'Bad request - missing reference or payment failed',
            'example': {
                "error": "Payment reference is required."
            }
        },
        403: {
            'description': 'Forbidden - user does not own this order',
            'example': {
                "error": "You don't have permission to access this order."
            }
        },
        404: {
            'description': 'Order not found',
            'example': {
                "error": "Order not found."
            }
        }
    }
)
class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        reference = request.query_params.get('reference', None)

        if not reference:
            return Response(
                {"error": "Payment reference is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = PaystackAPI.verify_payment(reference)

        if not result['status']:
            return Response(
                {"error": result['message']},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_data = result['data']

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

        payment_status = payment_data.get('status')
        amount = float(payment_data.get('amount', 0)) / 100
        currency = payment_data.get('currency', 'GHS')
        paid_at = payment_data.get('paid_at')

        if payment_status == 'success':
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

            if order.payment_status == Order.PAYMENT_PENDING:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    if order.payment_status == Order.PAYMENT_PENDING:
                        order.payment_status = Order.PAYMENT_COMPLETED
                        order.paystack_ref = reference
                        order.save()

                        from core.tasks import send_email_task
                        send_email_task(order.id)

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
            order = Order.objects.prefetch_related('items__product').get(id=order_id)

            customer = Customer.objects.get(user_id=request.user.id)
            if order.customer != customer:
                return Response(
                    {"error": "You don't have permission to access this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if order.payment_status == Order.PAYMENT_COMPLETED:
                return Response(
                    {"error": "This order has already been paid."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_amount = sum(
                (item.price_at_purchase * item.quantity) +
                (item.customization_price_at_purchase * item.quantity if item.with_customization else 0)
                for item in order.items.all()
            )

            if total_amount <= 0:
                return Response(
                    {"error": "Order total must be greater than zero."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            customer_email = request.user.email

            if not customer_email:
                return Response(
                    {"error": "Customer email is required for payment."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            callback_url = request.data.get('callback_url', None)

            result = PaystackAPI.initialize_payment(
                email=customer_email,
                amount=total_amount,
                order_id=order.id,
                callback_url=callback_url
            )

            if result['status']:
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
    permission_classes = []

    def post(self, request, *args, **kwargs):
        signature = request.headers.get('X-Paystack-Signature', '')

        if not signature:
            return Response(
                {"error": "No signature provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payload = request.body

        if not PaystackAPI.verify_webhook_signature(payload, signature):
            return Response(
                {"error": "Invalid signature"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST
            )

        event = webhook_data.get('event')

        if event == 'charge.success':
            return self._handle_successful_payment(webhook_data)

        elif event == 'charge.failed':
            return self._handle_failed_payment(webhook_data)

        return Response({"status": "received"}, status=status.HTTP_200_OK)

    def _handle_successful_payment(self, webhook_data):
        data = webhook_data.get('data', {})

        order_id = data.get('metadata', {}).get('order_id')

        if not order_id:
            print("Webhook received but no order_id in metadata")
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        reference = data.get('reference')
        payment_status = data.get('status')

        if not reference:
            print("Webhook received but no reference")
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

                if order.payment_status == Order.PAYMENT_PENDING:
                    if payment_status == 'success':
                        order.payment_status = Order.PAYMENT_COMPLETED
                        order.paystack_ref = reference
                        order.save()

                        from core.tasks import send_email_task
                        send_email_task(order.id)

                        print(f"✅ Order {order_id} payment confirmed via webhook")
                    else:
                        order.payment_status = Order.PAYMENT_FAILED
                        order.paystack_ref = reference
                        order.save()

                        print(f"⚠️ Order {order_id} marked as failed (unexpected status in charge.success)")
                else:
                    print(f"ℹ️ Order {order_id} already processed. Current status: {order.payment_status}")

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            print(f"❌ Webhook received for non-existent order: {order_id}")
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Error processing webhook for order {order_id}: {str(e)}")
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_failed_payment(self, webhook_data):
        data = webhook_data.get('data', {})

        order_id = data.get('metadata', {}).get('order_id')
        reference = data.get('reference')

        if not order_id or not reference:
            return Response({"status": "received"}, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)

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