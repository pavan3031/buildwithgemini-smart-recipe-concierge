import os
from google.cloud import firestore

# IMPORTANT: Hardcode project ID to avoid Agent Platform resolving to project number
FIRESTORE_PROJECT = "qwiklabs-gcp-02-16632a3e3848"

def seed_database():
    db = firestore.Client(project=FIRESTORE_PROJECT)
    recipes_ref = db.collection("recipes")

    sample_recipes = [
        {
            "id": "garlic-chicken-spinach",
            "title": "Garlic Butter Chicken & Spinach",
            "ingredients": ["chicken breast", "spinach", "garlic", "butter", "olive oil", "salt", "black pepper"],
            "instructions": "1. Season chicken with salt & pepper.\n2. Sear in olive oil until golden.\n3. Add butter and minced garlic.\n4. Toss in fresh spinach until wilted.\n5. Serve hot.",
            "prep_time_minutes": 25,
            "dietary_tags": ["gluten-free", "keto", "high-protein"],
            "servings": 2,
        },
        {
            "id": "quinoa-harvest-bowl",
            "title": "Quinoa Harvest Salad Bowl",
            "ingredients": ["quinoa", "sweet potato", "kale", "chickpeas", "tahini", "lemon juice"],
            "instructions": "1. Cook quinoa.\n2. Roast sweet potato cubes.\n3. Massage kale with lemon juice.\n4. Assemble bowl with chickpeas and drizzle with tahini dressing.",
            "prep_time_minutes": 20,
            "dietary_tags": ["vegan", "gluten-free", "vegetarian"],
            "servings": 2,
        },
        {
            "id": "basil-pesto-pasta",
            "title": "Classic Basil Pesto Pasta",
            "ingredients": ["penne pasta", "fresh basil", "pine nuts", "parmesan cheese", "garlic", "olive oil"],
            "instructions": "1. Boil pasta until al dente.\n2. Blend basil, pine nuts, garlic, parmesan, and olive oil.\n3. Toss warm pasta with pesto.",
            "prep_time_minutes": 15,
            "dietary_tags": ["vegetarian"],
            "servings": 4,
        },
        {
            "id": "berry-protein-smoothie",
            "title": "Berry Protein Smoothie Bowl",
            "ingredients": ["frozen mixed berries", "plant protein powder", "almond milk", "chia seeds", "sliced banana"],
            "instructions": "1. Blend berries, protein powder, and almond milk until thick.\n2. Pour into bowl and top with chia seeds and banana slices.",
            "prep_time_minutes": 5,
            "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
            "servings": 1,
        },
    ]

    for recipe in sample_recipes:
        doc_id = recipe["id"]
        recipes_ref.document(doc_id).set(recipe)
        print(f"Seeded recipe: {recipe['title']} ({doc_id})")

    print("\n✅ Firestore database successfully seeded!")

if __name__ == "__main__":
    seed_database()
