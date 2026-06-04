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
        return f"{self.species}, {self.tolid}"
    
    @property
    def total_pacbio_coverage(self):
        """Calculate total PacBio coverage from all runs"""
        runs = self.pacbio_runs.filter(coverage__isnull=False)
        total = sum(float(run.coverage) for run in runs if run.coverage)
        return round(total, 2) if total > 0 else None
    
    @property
    def total_hic_coverage(self):
        """Calculate total Hi-C coverage from all runs"""
        runs = self.hic_runs.filter(coverage__isnull=False)
        total = sum(float(run.coverage) for run in runs if run.coverage)
        return round(total, 2) if total > 0 else None

    @property
    def total_sequencing_coverage(self):
        """Calculate total coverage from all sequencing types"""
        pacbio = self.total_pacbio_coverage or 0
        hic = self.total_hic_coverage or 0
        total = pacbio + hic
        return round(total, 2) if total > 0 else None


class PacBioRun(models.Model):
    """PacBio sequencing run"""
    
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE, related_name='pacbio_runs')
    tissue_id = models.CharField("Tissue ID", max_length=20, blank = True)
    run_id = models.CharField("Run ID", max_length=100, unique=True)
    metadata_id = models.CharField("Metadata ID", max_length=100, blank=True)
    barcode = models.CharField(max_length=50, blank=True)
    hpc_filepath = models.CharField("HPC Filepath", max_length=100, blank=True)
    
    INSTRUMENT_CHOICES = [
        ('revio', 'Revio'),
        ('sequel_ii', 'Sequel II'),
    ]
    instrument = models.CharField(max_length=25, choices=INSTRUMENT_CHOICES, default="Revio")
    library_prep = models.CharField(max_length=255, blank=True)
    
    total_bases = models.BigIntegerField("Total Bases (bp)", null=True, blank=True, help_text="From SMRTLink output")
    coverage = models.DecimalField("Coverage (x)", max_digits=10, decimal_places=2, null=True, blank=True, help_text="Calculated from total bases / expected genome size")
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('processing', 'Processing'),
        ('failed', 'Processing failed'),
        ('complete', 'Complete'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    sequenced_by = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.run_id} - {self.individual.tol_id}"
    
    def save(self, *args, **kwargs):
        """Calculate coverage on save if total_bases is provided"""
        if self.total_bases and self.individual.expected_genome_size_bp and not self.coverage:
            self.coverage = self.total_bases / self.individual.expected_genome_size_bp
        super().save(*args, **kwargs)

class HiCRun(models.Model):
    """Hi-C sequencing run"""
    
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE, related_name='hic_runs')
    tissue_id = models.CharField("Tissue ID", max_length=20, blank = True)
    run_id = models.CharField("Run ID", max_length=100, unique=True)
    metadata_id = models.CharField("Metadata ID", max_length=100, blank=True)
    barcode = models.CharField(max_length=50, blank=True)
    genomeark_upload_filepath = models.CharField("GenomeArk Upload Filepath", max_length=100, blank=True)
    
    INSTRUMENT_CHOICES = [
        ('illumina_novaseq_6000', 'Illumina NovaSeq 6000'),
    ]
    instrument = models.CharField(max_length=25, choices=INSTRUMENT_CHOICES, default="Revio")
    LIBRARY_PREP_CHOICES = [
        ('arima_v2', 'Arima Hi-C v2'),
        ('dovetail_omni_c', 'Dovetail Omni-C'),
        ('arima_v1', 'Arima Hi-C v1'),
    ]
    library_prep = models.CharField(max_length=25, choices=LIBRARY_PREP_CHOICES, default = "Arima Hi-C v2")
    
    total_bases = models.BigIntegerField("Total Bases (bp)", null=True, blank=True, help_text="From SMRTLink output")
    coverage = models.DecimalField("Coverage (x)", max_digits=10, decimal_places=2, null=True, blank=True, help_text="Calculated from total bases / expected genome size")
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('processing', 'Processing'),
        ('failed', 'Processing failed'),
        ('complete', 'Complete'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    sequenced_by = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.run_id} - {self.individual.tol_id}"
    
    def save(self, *args, **kwargs):
        """Calculate coverage on save if total_bases is provided"""
        if self.total_bases and self.individual.expected_genome_size_bp and not self.coverage:
            self.coverage = self.total_bases / self.individual.expected_genome_size_bp
        super().save(*args, **kwargs)