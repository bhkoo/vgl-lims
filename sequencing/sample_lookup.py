import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

USERNAME = os.environ.get("FREEZERPRO_USERNAME")
PASSWORD = os.environ.get("FREEZERPRO_PASSWORD")
BASE_URL = os.environ.get("FREEZERPRO_BASE_URL", "https://rockefeller.freezerpro.com/api")

# UDF fields to retrieve
UDF_FIELDS = [
    "vgl_id", "sent_by", "collection_date", "collected_by", "geo_loc_name",
    "birth_date", "lat_lon", "mother", "father", "sex", "dev_stage",
    "description", "received_date", "store_cond", "treatment", "tissue"
]


def check_credentials():
    """Verify FreezerPro credentials are configured"""
    if not USERNAME or not PASSWORD:
        raise ValueError(
            "FreezerPro credentials not configured. "
            "Please set FREEZERPRO_USERNAME and FREEZERPRO_PASSWORD in .env file"
        )
    if not BASE_URL:
        raise ValueError("FREEZERPRO_BASE_URL not configured in .env file")

def search_by_tissue_id(tissue_id: str) -> dict:
    """
    Search FreezerPro for samples by Tissue ID (exact match).
    
    Args:
        tissue_id: Tissue ID to search for
    
    Returns:
        dict: API response from FreezerPro
    """
    try:
        check_credentials()
    except ValueError as e:
        logger.error(str(e))
        return {'error': str(e), 'success': False}
    
    try:
        # Search by tissue ID instead of vgl_id
        params = [
            ("method", "advanced_search"),
            ("query[][field]", "vgl_id"),
            ("query[][op]",    "contains"),
            ("query[][type]",  "udf"),
            ("query[][value]", tissue_id),
        ]
        
        for field in UDF_FIELDS:
            params.append(("udfs[]", field))
        
        logger.info(f"Querying FreezerPro for Tissue ID: {tissue_id}")
        
        response = requests.get(
            BASE_URL,
            params=params,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()

        results = data.get('Samples', [])
        total = data.get('Total', len(results))

        logger.info(f"FreezerPro query returned {len(results)} result(s)")
        
        return {
            'results': results,
            'count': total,
        }
        
    except requests.exceptions.Timeout:
        error_msg = f"FreezerPro request timed out for {field}: {tissue_id}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False, 'results': []}
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Failed to connect to FreezerPro: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False, 'results': []}
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"FreezerPro API error: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False, 'results': []}
    
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse FreezerPro response: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False, 'results': []}
    
    except Exception as e:
        error_msg = f"Unexpected error querying FreezerPro: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False, 'results': []}
