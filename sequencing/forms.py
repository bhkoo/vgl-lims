from django import forms
from .models import Individual, PacBioRun

class IndividualForm(forms.ModelForm):
    class Meta:
        model = Individual
        fields = ['species', 'tolid', 'vglid', 'taxid', 'expected_genome_size_bp', 'primary_contact', 
                  'primary_email', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

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
