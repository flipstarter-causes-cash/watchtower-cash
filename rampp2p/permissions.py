from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
  """
  Object-level permission to only allow admin access.
  """

  def has_permission(self, request, view):
    if request.method in SAFE_METHODS:
      return True
    return request.user and request.user.is_staff