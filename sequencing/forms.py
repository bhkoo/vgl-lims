from django import forms
from .models import Individual, PacBioRun, HiCRun

class IndividualForm(forms.ModelForm):
    class Meta:
        model = Individual
        fields = ['species', 'tolid', 'vglid', 'taxid', 'expected_genome_size_bp', 'primary_contact', 
                  'primary_email', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_species(self):
        """Replace underscores with spaces in species name"""
        species = self.cleaned_data.get('species', '')
        if species:
            species = species.replace('_', ' ')
        return species

class PacBioRunForm(forms.ModelForm):
    class Meta:
        model = PacBioRun
        fields = ['tissue_id', 'run_id', 'metadata_id', 'barcode', 'hpc_filepath', 'instrument', 
                  'library_prep', 'sequenced_by', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

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