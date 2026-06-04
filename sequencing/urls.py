from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('individual/entry/', views.individual_entry, name='individual_entry'),
    path('individual/list/', views.individual_list, name='individual_list'),
    path('sequencing/entry/', views.sequencing_entry, name='sequencing_entry'),
    path('sequencing/list/', views.sequencing_list, name='sequencing_list'),
    path('api/check-individual/', views.check_individual, name='check_individual'),
    path('api/lookup-species/', views.lookup_species, name='lookup_species'),
    path('sample/lookup/', views.sample_lookup, name='sample_lookup'), 
    path('api/sample-search/', views.sample_search, name='sample_search'),
]
