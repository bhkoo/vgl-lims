from django import forms
from .models import Individual, PacBioRun, HiCRun

class IndividualForm(forms.ModelForm):
    class Meta:
        model = Individual
        fields = ['species', 'subspecies', 'tolid', 'vglid', 'taxid', 'expected_genome_size_bp', 'primary_contact', 
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
    class Meta:
        model = PacBioRun
        fields = ['tissue_id', 'run_id', 'metadata_id', 'barcode', 'multiplexed', 'hpc_filepath', 'instrument', 
                  'library_prep', 'sequenced_by', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        """Check for duplicate combination of run_id, metadata_id, and barcode"""
        cleaned_data = super().clean()
        run_id = cleaned_data.get('run_id', '').strip()
        metadata_id = cleaned_data.get('metadata_id', '').strip()
        barcode = cleaned_data.get('barcode', '').strip()
        
        # Skip validation if this is a blank form
        if not run_id and not metadata_id and not barcode:
            return cleaned_data

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