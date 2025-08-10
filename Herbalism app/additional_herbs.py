#!/usr/bin/env python3
"""
Script to add more clean, well-known herbs to our database
"""
import pandas as pd

def get_additional_safe_herbs():
    """
    Add more common, well-known herbs with conservative safety info
    """
    additional_herbs = [
        {
            'id': 29,
            'name': 'Turmeric',
            'description': 'Perennial herb with bright orange rhizome, commonly used as spice.',
            'symbol': '🌿',
            'scientific_name': 'Curcuma longa',
            'traditional_uses': 'Culinary spice and traditional anti-inflammatory.',
            'current_evidence_summary': 'Some evidence for anti-inflammatory effects.',
            'contraindications': 'Avoid large amounts before surgery.',
            'interactions': 'May interact with blood thinning medications.',
            'toxicity_notes': 'Generally safe in culinary amounts.'
        },
        {
            'id': 30,
            'name': 'Clove',
            'description': 'Dried flower buds with strong aromatic properties.',
            'symbol': '🌿',
            'scientific_name': 'Syzygium aromaticum',
            'traditional_uses': 'Culinary spice and traditional dental pain relief.',
            'current_evidence_summary': 'Some evidence for antimicrobial effects.',
            'contraindications': 'Avoid large amounts during pregnancy.',
            'interactions': 'May interact with blood thinning medications.',
            'toxicity_notes': 'Generally safe in culinary amounts.'
        },
        {
            'id': 31,
            'name': 'Cinnamon',
            'description': 'Aromatic bark used as culinary spice.',
            'symbol': '🌿',
            'scientific_name': 'Cinnamomum verum',
            'traditional_uses': 'Culinary spice and traditional digestive aid.',
            'current_evidence_summary': 'Some evidence for blood sugar support.',
            'contraindications': 'Avoid large amounts during pregnancy.',
            'interactions': 'May interact with diabetes medications.',
            'toxicity_notes': 'Generally safe in culinary amounts.'
        },
        {
            'id': 32,
            'name': 'Cardamom',
            'description': 'Aromatic seeds in small pods, popular spice.',
            'symbol': '🌿',
            'scientific_name': 'Elettaria cardamomum',
            'traditional_uses': 'Culinary spice and traditional digestive aid.',
            'current_evidence_summary': 'Limited evidence for digestive benefits.',
            'contraindications': 'Avoid large amounts during pregnancy.',
            'interactions': 'May interact with blood thinning medications.',
            'toxicity_notes': 'Generally safe in culinary amounts.'
        },
        {
            'id': 33,
            'name': 'Star Anise',
            'description': 'Star-shaped seed pods with licorice-like flavor.',
            'symbol': '⭐',
            'scientific_name': 'Illicium verum',
            'traditional_uses': 'Culinary spice and traditional digestive aid.',
            'current_evidence_summary': 'Limited evidence for antimicrobial effects.',
            'contraindications': 'Avoid large amounts during pregnancy.',
            'interactions': 'May interact with hormone-sensitive medications.',
            'toxicity_notes': 'Generally safe in culinary amounts.'
        },
        {
            'id': 34,
            'name': 'Nettle',
            'description': 'Perennial herb with serrated leaves, requires careful handling.',
            'symbol': '🌿',
            'scientific_name': 'Urtica dioica',
            'traditional_uses': 'Traditional nutritive herb and allergy support.',
            'current_evidence_summary': 'Some evidence for allergy relief.',
            'contraindications': 'Avoid during pregnancy without medical supervision.',
            'interactions': 'May interact with diabetes and blood pressure medications.',
            'toxicity_notes': 'Fresh plant causes skin irritation.'
        },
        {
            'id': 35,
            'name': 'Burdock Root',
            'description': 'Large biennial plant with edible root.',
            'symbol': '🌿',
            'scientific_name': 'Arctium lappa',
            'traditional_uses': 'Traditional blood purifier and skin support.',
            'current_evidence_summary': 'Limited scientific evidence.',
            'contraindications': 'Avoid during pregnancy and breastfeeding.',
            'interactions': 'May interact with diabetes medications.',
            'toxicity_notes': 'Generally safe when properly prepared.'
        },
        {
            'id': 36,
            'name': 'Red Clover',
            'description': 'Perennial legume with red-pink flower heads.',
            'symbol': '🌸',
            'scientific_name': 'Trifolium pratense',
            'traditional_uses': 'Traditional womens health and respiratory support.',
            'current_evidence_summary': 'Limited evidence for menopausal symptoms.',
            'contraindications': 'Avoid with hormone-sensitive conditions.',
            'interactions': 'May interact with blood thinning medications.',
            'toxicity_notes': 'Generally safe in moderate amounts.'
        },
        {
            'id': 37,
            'name': 'Plantain',
            'description': 'Common perennial herb with ribbed leaves.',
            'symbol': '🌿',
            'scientific_name': 'Plantago major',
            'traditional_uses': 'Traditional wound care and respiratory support.',
            'current_evidence_summary': 'Limited evidence for wound healing.',
            'contraindications': 'Avoid large amounts during pregnancy.',
            'interactions': 'May interact with blood thinning medications.',
            'toxicity_notes': 'Generally safe for topical use.'
        },
        {
            'id': 38,
            'name': 'Elderberry',
            'description': 'Shrub with dark purple berries, white flowers.',
            'symbol': '🫐',
            'scientific_name': 'Sambucus canadensis',
            'traditional_uses': 'Traditional immune support and cold remedy.',
            'current_evidence_summary': 'Some evidence for cold and flu support.',
            'contraindications': 'Raw bark and leaves should be avoided.',
            'interactions': 'May interact with immune-suppressing medications.',
            'toxicity_notes': 'Berries generally safe when cooked; avoid raw bark and leaves.'
        }
    ]
    
    return additional_herbs

def add_herbs_to_csv():
    """Add new herbs to the existing CSV"""
    # Load current herbs
    current_df = pd.read_csv('herbs.csv')
    print(f"Current herbs: {len(current_df)}")
    
    # Get additional herbs
    additional_herbs = get_additional_safe_herbs()
    additional_df = pd.DataFrame(additional_herbs)
    
    # Combine
    combined_df = pd.concat([current_df, additional_df], ignore_index=True)
    
    # Save backup first
    current_df.to_csv('herbs_28_backup.csv', index=False)
    
    # Save expanded version
    combined_df.to_csv('herbs.csv', index=False)
    
    print(f"Added {len(additional_herbs)} new herbs")
    print(f"Total herbs now: {len(combined_df)}")
    print("\nNew herbs added:")
    for herb in additional_herbs:
        print(f"  - {herb['name']}")

if __name__ == "__main__":
    add_herbs_to_csv()