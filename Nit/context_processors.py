# context_processors.py
from .models import Assessment, Data


def sidebar_counts(request):
    return {
        'residential_count': Assessment.objects.filter(property_type='residential').count(),
        'commercial_count': Assessment.objects.filter(property_type='commercial').count(),
        'industrial_count': Assessment.objects.filter(property_type='industrial').count(),
        'map_count': Assessment.objects.filter(status='verified', latitude__isnull=False).count(),
    }


def data_list(request):
    return {
        'datas': Data.objects.all(),
    }