from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('individual/entry/', views.individual_entry, name='individual_entry'),
    path('individual/list/', views.individual_list, name='individual_list'),
    path('pacbio/entry/', views.pacbio_entry, name='pacbio_entry'),
    path('pacbio/list/', views.pacbio_list, name='pacbio_list'),
    path('pacbio/process/<str:run_id>/', views.process_run, name='process_run'),
    path('api/run-status/<str:run_id>/', views.run_status, name='run_status'),
    path('api/check-individual/', views.check_individual, name='check_individual'),
    path('api/lookup-species/', views.lookup_species, name='lookup_species'),
]
