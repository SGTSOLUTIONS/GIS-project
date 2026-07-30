from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if request.user.profile.role != 'admin' and not request.user.is_superuser:
                messages.error(request, 'Access denied. Admin only!')
                return redirect('home')
        except:
            messages.error(request, 'Access denied. Admin only!')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def surveyor_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if request.user.profile.role != 'surveyor':
                messages.error(request, 'Access denied. Surveyor only!')
                return redirect('home')
        except:
            messages.error(request, 'Access denied. Surveyor only!')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def cbe_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if request.user.profile.role != 'cbe':
                messages.error(request, 'Access denied. CBE only!')
                return redirect('home')
        except:
            messages.error(request, 'Access denied. CBE only!')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def taxcollector_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if request.user.profile.role != 'taxcollector':
                messages.error(request, 'Access denied. Tax Collector only!')
                return redirect('home')
        except:
            messages.error(request, 'Access denied. Tax Collector only!')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view