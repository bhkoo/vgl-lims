import re
from django import forms
from .models import Individual, PacBioRun, HiCRun

RUN_ID_PATTERN = re.compile(r'^r\d{5}_\d{8}_\d{6}$')
METADATA_ID_PATTERN = re.compile(r'^m\d{5}_\d{8}_\d{6}_s\d$')
BARCODE_PATTERN = re.compile(r'^bc\d{4}$')

# PacBio Sequencing Personnel
PACBIO_SEQUENCED_BY_CHOICES = [
    ('', '-- Select --'),
    ('jbalacco', 'Jennifer Balacco'),
    ('njain', 'Nivesh Jain'),
    ('external', 'External'),
]

# Hi-C Sequencing Personnel
HIC_SEQUENCED_BY_CHOICES = [
    ('', '-- Select --'),
    ('fackerman', 'Francine Ackerman'),
    ('botoole', 'Brian O\'Toole'),
]


class IndividualForm(forms.ModelForm):
    class Meta:
        model = Individual
        fields = ['species', 'subspecies', 'tolid', 'vglid', 'taxid', 'expected_genome_size_bp', 'primary_contact', 
                  'photo_url', 'photo_attribution', 'photo_source_url', 
                  'primary_email', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_species(self):
        species = self.cleaned_data.get('species', '')
        if species:
            species = species.replace('_', ' ')
        return species

class PacBioRunForm(forms.ModelForm):
    sequenced_by = forms.ChoiceField(choices=PACBIO_SEQUENCED_BY_CHOICES, required=True)

    class Meta:
        model = PacBioRun
        fields = ['tissue_id', 'run_id', 'metadata_id', 'barcode', 'multiplexed', 'hpc_filepath', 'instrument', 
                  'library_prep', 'sequenced_by', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_run_id(self):
        run_id = self.cleaned_data.get('run_id', '').strip()
        if run_id and not RUN_ID_PATTERN.match(run_id):
            raise forms.ValidationError(
                'Run ID must match format r[5 digits]_[YYYYMMDD]_[HHMMSS], e.g. r84091_20260625_203158'
            )
        return run_id

    def clean_metadata_id(self):
        metadata_id = self.cleaned_data.get('metadata_id', '').strip()
        if metadata_id and not METADATA_ID_PATTERN.match(metadata_id):
            raise forms.ValidationError(
                'Metadata ID must match format m[5 digits]_[YYYYMMDD]_[HHMMSS]_s[single digit], '
                'e.g. m84091_260627_030452_s1'
            )
        return metadata_id

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode', '').strip()
        if barcode and not BARCODE_PATTERN.match(barcode):
            raise forms.ValidationError('Barcode must match format bc[4 digits], e.g. bc1017')
        return barcode

    def clean(self):
        """Check for duplicate combination of run_id, metadata_id, and barcode"""
        cleaned_data = super().clean()
        run_id = cleaned_data.get('run_id', '').strip()
        metadata_id = cleaned_data.get('metadata_id', '').strip()
        barcode = cleaned_data.get('barcode', '').strip()
        hpc_filepath = cleaned_data.get('hpc_filepath', '').strip()
        
        # Skip validation if this is a blank form
        if not run_id and not metadata_id and not barcode:
            return cleaned_data
        
        # Filepath must contain the run ID
        if run_id and hpc_filepath and run_id not in hpc_filepath:
            raise forms.ValidationError(
                f'HPC Filepath must contain the Run ID "{run_id}".'
            )

        # Check if this exact combination already exists
        matching_runs = PacBioRun.objects.filter(
            run_id=run_id,
            metadata_id=metadata_id,
            barcode=barcode
        )
        
        if matching_runs.exists():
            raise forms.ValidationError(
                f'A run with Run ID "{run_id}", Metadata ID "{metadata_id}", '
                f'and Barcode "{barcode}" already exists in the database.'
            )
        
        return cleaned_data

# Formset for entering multiple PacBio runs at once
PacBioRunFormSet = forms.inlineformset_factory(
    Individual, 
    PacBioRun,
    form=PacBioRunForm,
    extra=1,  # Start with just 1 blank form
    can_delete=True
)

class HiCRunForm(forms.ModelForm):
    class Meta:
        model = HiCRun
        fields = ['tissue_id', 'run_id', 'metadata_id', 'barcode', 'genomeark_upload_filepath', 'instrument', 
                  'library_prep', 'sequenced_by', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

# Formset for entering multiple PacBio runs at once
HiCRunFormSet = forms.inlineformset_factory(
    Individual, 
    HiCRun,
    form=HiCRunForm,
    extra=1,  # Start with just 1 blank form
    can_delete=True
)