from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MenuItem, Cart
from .serializers import MenuItemSerializer, CartSerializer
from .permissions import IsManager, IsCustomer

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
