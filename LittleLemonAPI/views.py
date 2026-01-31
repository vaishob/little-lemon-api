from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import MenuItem, Cart, Order
from .serializers import (
    MenuItemSerializer,
    CartSerializer,
    OrderSerializer,
    OrderManagerUpdateSerializer,
    OrderDeliveryUpdateSerializer,
)
from .permissions import IsManager, IsDeliveryCrew, IsCustomer

# Create your views here.


class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # GET allowed for any authenticated user
        if self.request.method == "GET":
            return [IsAuthenticated()]
        # Write methods allowed only for Manager
        return [IsAuthenticated(), IsManager()]


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsManager()]


class CartView(generics.GenericAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    # GET /api/cart/menu-items
    def get(self, request):
        items = self.get_queryset()
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    # POST /api/cart/menu-items
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # user auto-injected by HiddenField
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # DELETE /api/cart/menu-items
    def delete(self, request):
        self.get_queryset().delete()
        return Response(status=status.HTTP_200_OK)


class OrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Manager: all orders
        if IsManager().has_permission(request, self):
            orders = Order.objects.all().order_by("-date", "-id")
            return Response(OrderSerializer(orders, many=True).data)

        # Delivery crew: assigned orders only
        if IsDeliveryCrew().has_permission(request, self):
            orders = Order.objects.filter(
                delivery_crew=user).order_by("-date", "-id")
            return Response(OrderSerializer(orders, many=True).data)

        # Customer: own orders only
        if IsCustomer().has_permission(request, self):
            orders = Order.objects.filter(user=user).order_by("-date", "-id")
            return Response(OrderSerializer(orders, many=True).data)

        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        # Only customers can checkout
        if not IsCustomer().has_permission(request, self):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrderSerializer(
            data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()  # creates order from cart + clears cart
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class SingleOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get_order_or_404(self, pk):
        try:
            return Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        order = self.get_order_or_404(pk)
        if order is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Manager can view any
        if IsManager().has_permission(request, self):
            return Response(OrderSerializer(order).data)

        # Customer can view only own
        if IsCustomer().has_permission(request, self) and order.user_id == request.user.id:
            return Response(OrderSerializer(order).data)

        # Delivery can view only assigned
        if IsDeliveryCrew().has_permission(request, self) and order.delivery_crew_id == request.user.id:
            return Response(OrderSerializer(order).data)

        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    def patch(self, request, pk):
        order = self.get_order_or_404(pk)
        if order is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Manager: can assign delivery_crew + update status
        if IsManager().has_permission(request, self):
            serializer = OrderManagerUpdateSerializer(
                order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

        # Deliver crew: status only, only if assigned
        if IsDeliveryCrew().has_permission(request, self):
            if order.delivery_crew_id != request.user.id:
                return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
            serializer = OrderDeliveryUpdateSerializer(
                order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

        return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

    # PUT behaves same as PATCH for this project

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        order = self.get_order_or_404(pk)
        if order is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Only manager can delete
        if not IsManager().has_permission(request, self):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        order.delete()
        return Response(status=status.HTTP_200_OK)
