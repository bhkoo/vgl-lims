from django.db import models
from django.utils import timezone

TISSUE_CHOICES = [
    ('BL', 'Blood'),
    ('MS', 'Muscle'),
    ('HT', 'Heart'),
    ('GL', 'Gill'),
    ('LV', 'Liver'),
    ('KD', 'Kidney'),
    ('SP', 'Spleen'),
    ('SK', 'Skin'),
    ('SM', 'Sperm'),
    ('EG', 'Egg'),
    ('OV', 'Ovary'),
    ('TS', 'Testis'),
    ('BR', 'Brain'),
    ('LG', 'Lung'),
    ('WB', 'Whole Body'),
    ('CL', 'Cells'),
    ('UK', 'Unknown'),
    ('MC', 'Misc'),
]

# Create your models here.
class Individual(models.Model):
    """An individual organism being sequenced"""
    
    tolid = models.CharField("ToLID", max_length=20, unique=True, primary_key=True)
    vglid = models.CharField("VGL ID", max_length=20, blank=True)
    species = models.CharField(max_length=255)
    taxid = models.IntegerField("NCBI Taxonomy ID", null=True, blank=True)
    expected_genome_size_bp = models.BigIntegerField("Expected Genome Size (bp)", null=True, blank=True)
    primary_contact = models.CharField(max_length=50, blank=True)
    primary_email = models.EmailField(max_length=50, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tolid} - {self.species}"


class PacBioRun(models.Model):
    """PacBio sequencing run"""
    
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE, related_name='pacbio_runs')
    tissue_id = models.CharField("Tissue ID", max_length=20, blank = True)
    run_id = models.CharField("Run ID", max_length=100, unique=True)
    metadata_id = models.CharField("Metadata ID", max_length=100, blank=True)
    barcode = models.CharField(max_length=6, blank=True)
    hpc_filepath = models.TextField("HPC Filepath", blank=True)
    
    INSTRUMENT_CHOICES = [
        ('revio', 'Revio'),
        ('sequel_ii', 'Sequel II'),
    ]
    instrument = models.CharField(max_length=20, choices=INSTRUMENT_CHOICES)
    library_prep = models.CharField(max_length=255, blank=True)
    
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('failed', 'Upload failed'),
        ('complete', 'Complete'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    sequenced_by = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.run_id} - {self.individual.tolid}"
