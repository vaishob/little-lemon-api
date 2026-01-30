from rest_framework.permissions import BasePermission


def _in_group(user, group_name: str) -> bool:
    return user and user.is_authenticated and user.groups.filter(name=group_name).exists()


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return _in_group(request.user, "Manager")


class IsDeliveryCrew(BasePermission):
    def has_permission(self, request, view):
        return _in_group(request.user, "Delivery crew")


class IsCustomer(BasePermission):
    """
    Authenticated user who is NOT in Manager or Delivery crew.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (not _in_group(user, "Manager")) and (not _in_group(user, "Delivery crew"))
