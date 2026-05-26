from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Individual, PacBioRun
from .forms import IndividualForm, PacBioRunFormSet
from .utils import augment_individual_data
from .pipeline import process_pacbio_run
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
    
    if not species:
        return JsonResponse({'error': 'No species provided'}, status=400)
    
    augmented_data = augment_individual_data(species)
    
    return JsonResponse({
        'species': species,
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

def pacbio_entry(request):
    """Form to add PacBio runs for an existing individual"""
    
    if request.method == 'POST':
        tolid = request.POST.get('tolid')
        
        try:
            individual = Individual.objects.get(tolid=tolid)
        except Individual.DoesNotExist:
            messages.error(request, f'Individual with ToLID "{tolid}" not found. Please add the individual first.')
            return redirect('pacbio_entry')
        
        formset = PacBioRunFormSet(request.POST, instance=individual)
        
        if formset.is_valid():
            runs = formset.save()
            count = len([r for r in runs if r is not None])
            messages.success(request, f'Successfully added {count} PacBio run(s) for {individual.tolid}')
            return redirect('pacbio_entry')
    else:
        formset = PacBioRunFormSet()
    
    return render(request, 'sequencing/pacbio_entry.html', {
        'formset': formset,
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

def process_run(request, run_id):
    """Manually trigger processing for a PacBio run"""
    try:
        run = PacBioRun.objects.get(run_id=run_id)
        
        # Run processing in background thread to avoid blocking
        thread = threading.Thread(
            target=process_pacbio_run,
            args=(run_id,),
            kwargs={'s3_bucket': 'genomeark'}  # Your S3 bucket
        )
        thread.start()
        
        messages.success(request, f'Started processing run {run_id}. Check back soon for results.')
        return redirect('pacbio_list')
        
    except PacBioRun.DoesNotExist:
        messages.error(request, f'Run {run_id} not found')
        return redirect('pacbio_list')
    
def run_status(request, run_id):
    """AJAX endpoint to check processing status"""
    try:
        run = PacBioRun.objects.get(run_id=run_id)
        return JsonResponse({
            'status': run.status,
            'total_bases': run.total_bases,
            'coverage': float(run.coverage) if run.coverage else None,
            'rdeval_s3_path': run.rdeval_s3_path,
            'processing_log': run.processing_log,
        })
    except PacBioRun.DoesNotExist:
        return JsonResponse({'error': 'Run not found'}, status=404)