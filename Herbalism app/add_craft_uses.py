#!/usr/bin/env python3
"""
Add craft_uses field to herbs.csv with non-medical applications
"""
import pandas as pd

def add_craft_uses_to_csv():
    """Add craft uses to existing herbs"""
    df = pd.read_csv('herbs.csv')
    
    # Add craft_uses column if it doesn't exist
    if 'craft_uses' not in df.columns:
        df['craft_uses'] = ''
    
    # Define craft uses for each herb
    craft_uses_data = {
        'Aloe Vera': 'Moisturizing gels, hair masks, natural skincare products.',
        'Angelica': 'Potpourri, herbal sachets, natural perfumes.',
        'Anise': 'Potpourri, natural air fresheners, soap scenting.',
        'Basil': 'Essential oils, culinary infusions, insect repellent sachets.',
        'Bay Leaf': 'Potpourri, natural moth repellent, aromatic sachets.',
        'Calendula': 'Natural soap colorant, gentle skincare products, botanical crafts.',
        'Chamomile': 'Hair lightening rinses, gentle facial steams, calming potpourri.',
        'Chives': 'Natural pest deterrent in gardens, culinary garnish.',
        'Coriander': 'Potpourri, soap scenting, natural deodorants.',
        'Dandelion': 'Natural yellow dye, botanical art, wild crafting projects.',
        'Dill': 'Potpourri, aromatic sachets, natural pickle flavoring.',
        'Echinacea': 'Botanical crafts, natural purple dye, dried flower arrangements.',
        'Eucalyptus': 'Essential oils, shower bundles, natural decongestant steams, potpourri.',
        'Fennel': 'Potpourri, natural breath fresheners, soap scenting.',
        'Garlic': 'Natural pest deterrent, garden companion planting.',
        'Ginger': 'Warming bath soaks, natural hair treatments, soap scenting.',
        'Lavender': 'Essential oils, potpourri, sachets, natural fabric softener, soap making.',
        'Lemon Balm': 'Natural furniture polish, potpourri, insect repellent sachets.',
        'Marjoram': 'Potpourri, natural air fresheners, soap scenting.',
        'Mint': 'Natural cooling foot soaks, potpourri, pest deterrent, toothpaste flavoring.',
        'Oregano': 'Natural preservative, soap scenting, potpourri.',
        'Parsley': 'Natural breath freshener, hair rinses, botanical crafts.',
        'Peppermint': 'Essential oils, cooling foot soaks, natural pest deterrent, lip balms.',
        'Rosemary': 'Hair growth rinses, natural preservative, potpourri, essential oils.',
        'Sage': 'Smudging bundles, natural deodorants, hair rinses, potpourri.',
        'Thyme': 'Natural preservative, potpourri, soap scenting, essential oils.',
        'Valerian': 'Sleep sachets, potpourri, natural fabric freshener.',
        'Yarrow': 'Natural wound powder, botanical crafts, dried flower arrangements.',
        'Turmeric': 'Natural yellow dye, face masks, soap colorant, golden milk lattes.',
        'Clove': 'Natural air freshener, potpourri, soap scenting, dental care products.',
        'Cinnamon': 'Potpourri, natural air freshener, soap scenting, warming bath soaks.',
        'Cardamom': 'Natural breath freshener, potpourri, soap scenting.',
        'Star Anise': 'Potpourri, natural air freshener, decorative crafts.',
        'Nettle': 'Natural fiber for textiles, hair growth rinses, green dye.',
        'Burdock Root': 'Hair care products, natural soap making.',
        'Red Clover': 'Natural pink dye, botanical crafts, flower arrangements.',
        'Plantain': 'Natural first aid balms, botanical crafts.',
        'Elderberry': 'Natural purple dye, syrup making, flower fritters.'
    }
    
    # Update the dataframe with craft uses
    for index, row in df.iterrows():
        herb_name = row['name']
        if herb_name in craft_uses_data:
            df.at[index, 'craft_uses'] = craft_uses_data[herb_name]
        else:
            df.at[index, 'craft_uses'] = 'Potpourri, botanical crafts.'
    
    # Save updated CSV
    df.to_csv('herbs.csv', index=False)
    print(f"Added craft uses to {len(df)} herbs")
    print("Sample craft uses:")
    for herb in ['Lavender', 'Eucalyptus', 'Rosemary', 'Turmeric']:
        if herb in craft_uses_data:
            print(f"  {herb}: {craft_uses_data[herb]}")

if __name__ == "__main__":
    add_craft_uses_to_csv()