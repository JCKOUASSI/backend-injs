from rest_framework import permissions


class HasModulePermission(permissions.BasePermission):
    """Vérifie la permission module.action via les groupes Django."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        module = getattr(view, 'permission_module', None)
        action_map = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        action = getattr(view, 'permission_action', None) or action_map.get(request.method, 'view')
        if not module:
            return True
        return request.user.has_module_permission(module, action)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        context = {}
        if hasattr(obj, 'student_id'):
            context['student_id'] = str(obj.student_id)
        if hasattr(obj, 'teacher_id'):
            context['teacher_id'] = str(obj.teacher_id)
        module = getattr(view, 'permission_module', None)
        action_map = {'GET': 'view', 'PUT': 'update', 'PATCH': 'update', 'DELETE': 'delete'}
        action = getattr(view, 'permission_action', None) or action_map.get(request.method, 'view')
        if module:
            return request.user.has_module_permission(module, action, context)
        return True


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.get_group_level() <= 2
        )
