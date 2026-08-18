from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Individual, PacBioRun, HiCRun
from .forms import IndividualForm, PacBioRunFormSet, HiCRunFormSet
from .utils import augment_individual_data
from .sample_lookup import search_by_tissue_id
import threading

def home(request):
    """Home page with navigation"""
    stats = {
        'individuals': Individual.objects.count(),
        'pacbio_runs': PacBioRun.objects.count(),
    }
    return render(request, 'sequencing/home.html')

def individual_entry(request):
    """Form to add a new individual"""
    
    if request.method == 'POST':
        form = IndividualForm(request.POST)
        
        if form.is_valid():
            individual = form.save(commit = False)
            if not individual.taxid or not individual.expected_genome_size_bp:
                augmented_data = augment_individual_data(individual.species)
                
                if not individual.taxid and augmented_data['taxid']:
                    individual.taxid = augmented_data['taxid']
                
                if not individual.expected_genome_size_bp and augmented_data['genome_size']:
                    individual.expected_genome_size_bp = augmented_data['genome_size']
            
            individual.save()
            
            messages.success(
                request, 
                f'Successfully added {individual.species}, {individual.tolid}'
            )
            return redirect('individual_entry')
    else:
        form = IndividualForm()
    
    return render(request, 'sequencing/individual_entry.html', {
        'form': form,
    })

def lookup_species(request):
    """AJAX endpoint to lookup species data from NCBI and GoaT"""
    species = request.GET.get('species', '').strip()
    subspecies = request.GET.get('subspecies', '').strip()
    
    if not species:
        return JsonResponse({'error': 'No species provided'}, status=400)
    
    # Combine species and subspecies for the search query
    search_term = f"{species} {subspecies}".strip() if subspecies else species
    
    augmented_data = augment_individual_data(search_term)
    
    return JsonResponse({
        'species': species,
        'subspecies': subspecies,
        'taxid': augmented_data['taxid'],
        'genome_size': augmented_data['genome_size'],
    })

def check_individual(request):
    """AJAX endpoint to check if individual exists and return details"""
    tolid = request.GET.get('tolid', '').strip()
    
    if not tolid:
        return JsonResponse({'exists': False})
    
    try:
        individual = Individual.objects.get(tolid=tolid)
        return JsonResponse({
            'exists': True,
            'vglid': individual.vglid,
            'species': individual.species,
            'taxid': individual.taxid,
            'expected_genome_size': individual.expected_genome_size_bp,
        })
    except Individual.DoesNotExist:
        return JsonResponse({'exists': False})

def sequencing_entry(request):
    """Unified form to add sequencing runs (PacBio or Hi-C)"""
    
    pacbio_formset = None
    hic_formset = None
    
    if request.method == 'POST':
        tolid = request.POST.get('tolid')
        sequencing_type = request.POST.get('sequencing_type')
        
        try:
            individual = Individual.objects.get(tolid=tolid)
        except Individual.DoesNotExist:
            messages.error(request, f'Individual with ToLID "{tolid}" not found. Please add the individual first.')
            return redirect('sequencing_entry')
        
        if sequencing_type == 'pacbio':
            pacbio_formset = PacBioRunFormSet(request.POST, instance=individual)
            
            if not pacbio_formset.is_valid():
                for form_idx, form in enumerate(pacbio_formset):
                    if form.errors:
                        for field, errors in form.errors.items():
                            for error in errors:
                                if field == '__all__':
                                    messages.error(request, f'Error: {error}')
                                else:
                                    messages.error(request, f'Error ({field}): {error}')
                
                for error in pacbio_formset.non_form_errors():
                    messages.error(request, f'Error: {error}')
                
                hic_formset = HiCRunFormSet()
            else:
                runs = pacbio_formset.save()
                count = len([r for r in runs if r is not None])
                messages.success(request, f'Successfully added {count} PacBio run(s) for {individual.tolid}')
                return redirect('sequencing_entry')
                
        elif sequencing_type == 'hic':
            hic_formset = HiCRunFormSet(request.POST, instance=individual)
            
            if hic_formset.is_valid():
                # Get current highest run_number for this individual
                existing_count = individual.hic_runs.count()
                
                instances = hic_formset.save(commit=False)
                next_number = existing_count + 1
                
                for instance in instances:
                    instance.individual = individual
                    instance.run_number = next_number
                    instance.save()
                    next_number += 1
                
                # Handle any deleted forms
                for obj in hic_formset.deleted_objects:
                    obj.delete()
                
                count = len(instances)
                messages.success(request, f'Successfully added {count} Hi-C run(s) for {individual.tolid}')
                return redirect('sequencing_entry')
            else:
                for form in hic_formset:
                    if form.errors:
                        for field, errors in form.errors.items():
                            for error in errors:
                                if field == '__all__':
                                    messages.error(request, f'Error: {error}')
                                else:
                                    messages.error(request, f'Error ({field}): {error}')
                pacbio_formset = PacBioRunFormSet()
        else:
            messages.error(request, 'Invalid sequencing type')
            return redirect('sequencing_entry')
    else:
        pacbio_formset = PacBioRunFormSet()
        hic_formset = HiCRunFormSet()
    
    return render(request, 'sequencing/sequencing_entry.html', {
        'pacbio_formset': pacbio_formset,
        'hic_formset': hic_formset,
    })

def sequencing_list(request):
    """View all sequencing runs"""
    individuals = Individual.objects.prefetch_related('pacbio_runs', 'hic_runs').all()
    return render(request, 'sequencing/sequencing_list.html', {
        'individuals': individuals,
    })

def check_individual(request):
    """AJAX endpoint to check if individual exists and return details"""
    tolid = request.GET.get('tolid', '').strip()
    
    if not tolid:
        return JsonResponse({'exists': False})
    
    try:
        individual = Individual.objects.get(tolid=tolid)
        return JsonResponse({
            'exists': True,
            'vglid': individual.vglid,
            'species': individual.species,
        })
    except Individual.DoesNotExist:
        return JsonResponse({'exists': False})

def individual_list(request):
    """View all individuals"""
    individuals = Individual.objects.all()
    return render(request, 'sequencing/individual_list.html', {
        'individuals': individuals,
    })

def pacbio_list(request):
    """View all individuals and their PacBio runs"""
    individuals = Individual.objects.prefetch_related('pacbio_runs').all()
    return render(request, 'sequencing/pacbio_list.html', {
        'individuals': individuals,
    })

def sample_lookup(request):
    """Page to lookup sample data from FreezerPro"""
    return render(request, 'sequencing/sample_lookup.html')


def sample_search(request):
    """AJAX endpoint to search FreezerPro"""
    search_value = request.GET.get('search_value', '').strip()
    
    if not search_value:
        return JsonResponse({'error': 'Search value required'}, status=400)
    
    try:
        results = search_by_tissue_id(search_value)
        return JsonResponse(results)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
