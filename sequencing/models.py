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
    
    # Calculated/processed fields
    bam_filepath = models.TextField("BAM Filepath", blank=True, help_text="Auto-generated from HPC filepath")
    fastq_filepath = models.TextField("FASTQ Filepath", blank=True, help_text="Generated fastq.gz file")
    total_bases = models.BigIntegerField("Total Bases", null=True, blank=True, help_text="Total basepairs in fastq file")
    coverage = models.DecimalField("Coverage", max_digits=6, decimal_places=2, null=True, blank=True, help_text="Calculated coverage (x)")

    INSTRUMENT_CHOICES = [
        ('revio', 'Revio'),
        ('sequel_ii', 'Sequel II'),
    ]
    instrument = models.CharField(max_length=20, choices=INSTRUMENT_CHOICES)
    library_prep = models.CharField(max_length=255, blank=True)
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('processing', 'Processing'),
        ('failed', 'Processing failed'),
        ('complete', 'Complete'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    sequenced_by = models.CharField(max_length=255, blank=True)
    
    processing_log = models.TextField(blank=True, help_text="Log of processing steps")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.run_id} - {self.individual.tolid}"

    def save(self, *args, **kwargs):
        """Override save to trigger processing if hpc_filepath is set"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-trigger processing for new runs with filepath
        if is_new and self.hpc_filepath and self.status == 'planned':
            from .pipeline import process_pacbio_run
            import threading
            
            thread = threading.Thread(
                target=process_pacbio_run,
                args=(self.run_id,),
                kwargs={'s3_bucket': 'genomeark'}
            )
            thread.start()