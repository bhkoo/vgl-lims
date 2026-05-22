from django.contrib import admin
from .models import Individual, PacBioRun

# Register your models here.

class PacBioRunInline(admin.TabularInline):
    """Show PacBio runs inline when viewing an individual"""
    model = PacBioRun
    extra = 1  # Shows one empty form to add a new run
    fields = ['run_id', 'metadata_id', 'barcode', 'hpc_filepath', 'instrument', 'status', 'sequenced_by']

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    list_display = ['tolid', 'vglid', 'species', 'created_at', 'primary_contact', 'primary_email']
    search_fields = ['tolid', 'vglid', 'species', 'primary_contact']
    list_filter = ['species']
    inlines = [PacBioRunInline]
    
    fieldsets = (
        ('Individual Information', {
            'fields': ('tolid', 'vglid', 'species')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

@admin.register(PacBioRun)
class PacBioRunAdmin(admin.ModelAdmin):
    list_display = ['run_id', 'individual', 'instrument', 'status', 'sequenced_by', 'created_at']
    search_fields = ['run_id', 'metadata_id', 'individual__tolid', 'individual__species']
    list_filter = ['instrument', 'status', 'sequenced_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Individual', {
            'fields': ('individual',)
        }),
        ('Run Information', {
            'fields': ('run_id', 'metadata_id', 'barcode', 'hpc_filepath')
        }),
        ('Sequencing Details', {
            'fields': ('instrument', 'library_prep', 'status', 'sequenced_by')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
