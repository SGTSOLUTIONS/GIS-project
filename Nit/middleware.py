from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class RoleMiddleware:
    """
    Middleware to handle role-based redirection
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Handle role-based redirection for root URLs
        """
        if request.user.is_authenticated:
            try:
                role = request.user.profile.role
            except:
                return None

            # Redirect to role-specific dashboard for root URL
            if request.path == '/':
                if role == 'admin':
                    return redirect('admin_dashboard')
                elif role == 'surveyor':
                    return redirect('surveyor_dashboard')
                elif role == 'cbe':
                    return redirect('cbe_dashboard')
                elif role == 'taxcollector':
                    return redirect('taxcollector_dashboard')

        return None