from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Category, MenuItem, Cart, Order, OrderItem

# ---- Basic / utility serializers ----


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "title"]


class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = MenuItem
        fields = ["id", "title", "price",
                  "featured", "category", "category_id"]

    def create(self, validated_data):
        category_id = validated_data.pop("category_id")
        validated_data["category_id"] = category_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category_id = validated_data.pop("category_id", None)
        if category_id is not None:
            instance.category_id = category_id
        return super().update(instance, validated_data)


# ---- Cart ----

class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    menuitem = MenuItemSerializer(read_only=True)
    menuitem_id = serializers.IntegerField(write_only=True, required=True)

    unit_price = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True)
    price = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "menuitem", "menuitem_id",
                  "quantity", "unit_price", "price"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0.")
        return value

    def create(self, validated_data):
        """
        Enforces: (menuitem, user) unique_together.
        If the item already exists in cart, update quantity instead of erroring.
        """
        user = validated_data["user"]
        menuitem_id = validated_data.pop("menuitem_id")
        quantity = validated_data["quantity"]

        menuitem = MenuItem.objects.get(pk=menuitem_id)
        unit_price = menuitem.price
        price = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"))

        cart_item, created = Cart.objects.get_or_create(
            user=user,
            menuitem=menuitem,
            defaults={
                "quantity": quantity,
                "unit_price": unit_price,
                "price": price,
            },
        )

        if not created:
            # Update existing row: add to quantity
            cart_item.quantity = cart_item.quantity + quantity
            cart_item.unit_price = unit_price
            cart_item.price = (Decimal(cart_item.quantity)
                               * unit_price).quantize(Decimal("0.01"))
            cart_item.save()

        return cart_item


# ---- Orders ----

class OrderItemSerializer(serializers.ModelSerializer):
    menuitem = MenuItemSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "menuitem", "quantity", "unit_price", "price"]


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    items = OrderItemSerializer(
        many=True, read_only=True, source="orderitem_set")

    total = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True)
    status = serializers.BooleanField(read_only=True)
    deliver_crew = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "delivery_crew",
                  "status", "total", "date", "items"]
        read_only_fields = ["date"]

    def create(self, validated_data):
        """
        Customer checkout:
        - Read cart items for request.user
        - Create Order + OrderItems
        - Delete cart items
        """
        user = validated_data["user"]
        cart_items = Cart.objects.filter(user=user)

        if not cart_items.exists():
            raise serializers.ValidationError("Cart is empty.")

        order = Order.objects.create(
            user=user,
            status=False,
            total=Decimal("0.00"),
            date=timezone.now().date(),
        )

        total = Decimal("0.00")
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=cart_item.menuitem,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                price=cart_item.price,
            )
            total += cart_item.price

        order.total = total.quantize(Decimal("0.01"))
        order.save()

        cart_items.delete()
        return order
