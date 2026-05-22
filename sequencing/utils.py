import requests
import subprocess
import json
import logging

logger = logging.getLogger(__name__)


def get_ncbi_taxid(species_name):
    """
    Get NCBI taxonomy ID for a species using NCBI datasets CLI.
    
    Args:
        species_name: Scientific name of the species (e.g., "Equus caballus")
    
    Returns:
        int: NCBI taxonomy ID, or None if not found
    """
    try:
        # Run the datasets command
        result = subprocess.run(
            ['datasets', 'summary', 'taxonomy', 'taxon', species_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # Parse the JSON response to extract taxonomy ID
            # The structure is: data['reports'][0]['taxonomy']['tax_id']
            if 'reports' in data and len(data['reports']) > 0:
                tax_id = data['reports'][0]['taxonomy']['tax_id']
                return int(tax_id)
        
        logger.warning(f"Could not find NCBI taxon ID for species: {species_name}")
        return None
        
    except FileNotFoundError:
        logger.error("NCBI datasets CLI not found. Install it from: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/download-and-install/")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while fetching NCBI taxon ID for {species_name}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Error parsing NCBI response for {species_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching NCBI taxon ID for {species_name}: {e}")
        return None


def get_expected_genome_size(taxon_id):
    """
    Get expected genome size from Genome on a Tree (GoaT) API.
    
    Args:
        taxon_id: NCBI taxonomy ID
    
    Returns:
        int: Expected genome size in base pairs, or None if not found
    """
    try:
        url = f"https://goat.genomehubs.org/api/v2/record?recordId={taxon_id}&result=taxon&taxonomy=ncbi"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Navigate the JSON structure
        if 'records' in data and len(data['records']) > 0:
            record = data['records'][0]['record']
            if 'attributes' in record and 'genome_size' in record['attributes']:
                genome_size = record['attributes']['genome_size'].get('value')
                if genome_size:
                    return int(genome_size)
        
        logger.warning(f"Could not find genome size for taxon ID: {taxon_id}")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Error fetching genome size from GoaT for taxon {taxon_id}: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing GoaT response for taxon {taxon_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching genome size for taxon {taxon_id}: {e}")
        return None


def augment_individual_data(species_name):
    """
    Get both NCBI taxon ID and expected genome size for a species.
    
    Args:
        species_name: Scientific name of the species
    
    Returns:
        dict: {'taxid': int or None, 'genome_size': int or None}
    """
    result = {
        'taxid': None,
        'genome_size': None
    }
    
    # Get taxon ID
    taxid = get_ncbi_taxid(species_name)
    result['taxid'] = taxid
    
    # If we got a taxon ID, try to get genome size
    if taxid:
        genome_size = get_expected_genome_size(taxid)
        result['genome_size'] = genome_size
    
    return result