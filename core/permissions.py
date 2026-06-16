from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    message = "Only administrators are allowed to perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'

class IsWarehouseManagerOrAdmin(BasePermission):
    message = "Only warehouse managers or administrators are allowed to perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ('ADMIN', 'WAREHOUSE_MANAGER')

class IsProcurementManagerOrAdmin(BasePermission):
    message = "Only procurement managers or administrators are allowed to perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ('ADMIN', 'PROCUREMENT_MANAGER')

class IsWarehouseManagerOrAdminOrStaff(BasePermission):
    message = "Only staff, warehouse managers, or administrators are allowed to perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ('ADMIN', 'WAREHOUSE_MANAGER', 'STAFF')

class IsOwnerOrAdmin(BasePermission):
    message = "Only the owner or an administrator can access this resource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admins have access to everything
        if request.user.role == 'ADMIN':
            return True

        # Check ownership dynamically looking for 'created_by' or 'performed_by'
        owner = None
        if hasattr(obj, 'created_by'):
            owner = obj.created_by
        elif hasattr(obj, 'performed_by'):
            owner = obj.performed_by

        return owner == request.user

class IsReportViewer(BasePermission):
    message = "Only administrators, warehouse managers, or procurement managers are allowed to view reports."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ('ADMIN', 'WAREHOUSE_MANAGER', 'PROCUREMENT_MANAGER')
