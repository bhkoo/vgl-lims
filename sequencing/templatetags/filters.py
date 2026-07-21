from django import template

register = template.Library()

@register.filter
def format_genome_size(value):
    """
    Convert base pairs to Gbp or Mbp for display.
    
    Examples:
        3000000000 -> "3.0 Gbp"
        500000000 -> "500 Mbp"
    """
    if not value:
        return "—"
    
    value = int(value)
    
    # Convert to Gbp
    if value >= 1_000_000_000:
        gbp = value / 1_000_000_000
        return f"{gbp:.2f} Gbp"
    
    # Convert to Mbp
    if value >= 1_000_000:
        mbp = value / 1_000_000
        return f"{mbp:.0f} Mbp"
    
    # Keep as bp
    return f"{value:,} bp"

@register.simple_tag
def ncbi_taxon_link(taxon_id):
    """Generate NCBI taxonomy browser link"""
    if not taxon_id:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/datasets/taxonomy/browser/?taxon={taxon_id}"