# LM Studio Setup for Pans Cookbook

This document contains all the AI prompts and configuration needed to set up LM Studio for the Pans Cookbook application.

## LM Studio Configuration

**Default URL:** `http://localhost:1234/v1`
**Model Recommendation:** Any instruct-tuned model (e.g., Llama, Mistral, CodeLlama)
**Settings:**
- Max Tokens: 2000
- Temperature: 0.3 (for structured output)
- Temperature: 0.7 (for creative suggestions)

## Core AI Prompts

### 1. Recipe Scraping Enhancement

**Purpose:** Extract structured recipe data from HTML content
**Temperature:** 0.3
**Max Tokens:** 1500

```
Analyze this recipe webpage HTML and extract structured recipe information:

URL: {url}
HTML Content: {html_snippet}

Please extract and return ONLY a JSON object with these fields:
{
    "title": "recipe name",
    "description": "brief description",  
    "ingredients": ["ingredient 1", "ingredient 2"],
    "instructions": "step-by-step instructions",
    "prep_time": "15 minutes",
    "cook_time": "30 minutes", 
    "servings": "4",
    "cuisine": "cuisine type",
    "difficulty": "easy/medium/hard",
    "dietary_tags": ["vegetarian", "gluten-free"]
}

Focus on accuracy and completeness. Return only valid JSON.
```

### 2. Ingredient Suggestions

**Purpose:** Suggest complementary ingredients or substitutes
**Temperature:** 0.7
**Max Tokens:** 300

```
Recipe: {recipe_title}
Current ingredients: {ingredient_list}
Available ingredients: {pantry_ingredients}

Suggest 3-5 additional ingredients that would complement this recipe or substitutes for ingredients the user doesn't have.
Focus on practical, commonly available ingredients.

Return only a JSON array of ingredient names:
["suggestion 1", "suggestion 2", "suggestion 3"]
```

### 3. Instruction Improvement

**Purpose:** Enhance cooking instructions for clarity
**Temperature:** 0.5
**Max Tokens:** 800

```
Recipe: {recipe_title}
Current instructions: {current_instructions}

Please improve these cooking instructions to be clearer, more detailed, and easier to follow.
Add helpful tips, timing guidance, and visual cues where appropriate.
Keep the same cooking method but make it more accessible for home cooks.

Return only the improved instructions as plain text.
```

### 4. Nutrition Estimation

**Purpose:** Estimate nutritional information per serving
**Temperature:** 0.3
**Max Tokens:** 200

```
Recipe: {recipe_title}
Servings: {servings}
Ingredients: {ingredient_list}

Estimate the nutritional information per serving for this recipe.
Return ONLY a JSON object:
{
    "calories": 350,
    "protein_g": 25,
    "carbs_g": 30,
    "fat_g": 15,
    "fiber_g": 5,
    "sugar_g": 8
}

Provide reasonable estimates based on typical ingredient nutritional values.
```

### 5. AI Ingredient Parsing

**Purpose:** Parse raw ingredient text into structured format
**Temperature:** 0.2
**Max Tokens:** 1000

```
Parse these recipe ingredients into structured format. For each ingredient, extract:
- quantity (number)
- unit (measurement)
- name (ingredient name)
- preparation (optional cooking notes)

Ingredients to parse:
{raw_ingredients}

Return as JSON array:
[
    {
        "original_text": "2 cups flour, sifted",
        "quantity": 2,
        "unit": "cups", 
        "name": "flour",
        "preparation": "sifted"
    }
]

If quantity/unit cannot be determined, use null. Focus on accuracy.
```

### 6. Recipe Classification

**Purpose:** Classify and tag recipes automatically
**Temperature:** 0.3
**Max Tokens:** 200

```
Analyze this recipe and classify it:

Title: {recipe_title}
Ingredients: {ingredients}
Instructions: {instructions}

Return ONLY a JSON object:
{
    "cuisine_type": "italian/mexican/asian/american/etc",
    "meal_category": "breakfast/lunch/dinner/dessert/snack",
    "difficulty_level": "easy/medium/hard",
    "dietary_tags": ["vegetarian", "gluten-free", "dairy-free", "etc"],
    "cooking_methods": ["baking", "frying", "grilling", "etc"]
}
```

## LM Studio Model Recommendations

### Primary Models (Recommended)
1. **Llama 3.1 8B Instruct** - Best balance of performance and speed
2. **Mistral 7B Instruct** - Good for structured output
3. **CodeLlama 7B Instruct** - Excellent for JSON parsing

### Advanced Models (If you have sufficient hardware)
1. **Llama 3.1 70B** - Superior quality but requires powerful hardware
2. **Mixtral 8x7B** - Good balance for complex tasks

## API Integration Code

### Python Request Example
```python
import requests
import json

def call_lm_studio(prompt, max_tokens=500, temperature=0.3):
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            print(f"Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"API call failed: {e}")
        return None
```

## Testing the Setup

### 1. Health Check
```python
def test_lm_studio_connection():
    test_prompt = "Say 'Hello' and return just the word 'Hello'"
    response = call_lm_studio(test_prompt, max_tokens=10, temperature=0.1)
    return response and "hello" in response.lower()
```

### 2. JSON Parsing Test
```python
def test_json_parsing():
    prompt = '''Return this as JSON: {"test": "success", "number": 42}'''
    response = call_lm_studio(prompt, max_tokens=50, temperature=0.1)
    try:
        json.loads(response)
        return True
    except:
        return False
```

## Common Issues & Solutions

### Issue: Connection Refused
**Solution:** Ensure LM Studio is running and has a model loaded

### Issue: JSON Parsing Errors
**Solution:** Lower temperature (0.1-0.3) and be very specific in prompts about JSON format

### Issue: Slow Responses
**Solution:** Reduce max_tokens, use smaller model, or increase timeout

### Issue: Inconsistent Results
**Solution:** Lower temperature and add more specific instructions

## Prompt Engineering Tips

1. **Be Specific:** Always specify the exact output format you want
2. **Use Examples:** Include example JSON in prompts when possible
3. **Set Context:** Provide clear context about the task
4. **Error Handling:** Always validate JSON responses before using
5. **Temperature Settings:**
   - 0.1-0.3: Structured output, JSON parsing
   - 0.5-0.7: Creative suggestions, improvements
   - 0.8+: Creative writing, variations

## Integration with Pans Cookbook

The AI service automatically:
1. Checks LM Studio availability on startup
2. Falls back gracefully when AI is unavailable
3. Caches results to reduce API calls
4. Provides structured error handling
5. Validates all JSON responses

All prompts are integrated into the `AIService` class in `services/ai_service.py`.