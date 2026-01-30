from django.contrib import admin
from .models import Category, MenuItem, Cart, Order, OrderItem

# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "slug")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "featured", "category")
    list_filter = ("featured", "category")
    search_fields = ("title",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "menuitem",
                    "quantity", "unit_price", "price")
    list_filter = ("user",)
    search_fields = ("user__username", "menuitem__title")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery_crew", "status", "total", "date")
    list_filter = ("status", "date", "delivery_crew")
    search_fields = ("user__username", "delivery_crew__username")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menuitem",
                    "quantity", "unit_price", "price")
    list_filter = ("menuitem",)
    search_fields = ("order__id", "menuitem__title")
