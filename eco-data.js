/**
 * Eco-Nudge Negotiator - Environmental & Nutritional Data Module
 * 
 * Contains carbon footprint data (kg CO2e per kg of food),
 * nutritional information, and sustainable substitution mappings.
 * 
 * Data sources:
 * - Poore & Nemecek (2018), Science: "Reducing food's environmental impacts"
 * - Our World in Data: Environmental impacts of food production
 * - USDA FoodData Central for nutritional values
 */

const EcoData = (() => {

    // Carbon footprint in kg CO2e per kg of food product
    const carbonFootprint = {
        // Meats (high impact)
        'beef': 27.0,
        'lamb': 24.0,
        'pork': 7.6,
        'chicken': 6.9,
        'turkey': 5.5,
        'bacon': 8.0,
        'sausage': 7.0,
        'salami': 8.5,
        'ham': 7.2,

        // Seafood
        'shrimp': 11.8,
        'prawns': 11.8,
        'salmon': 5.4,
        'tuna': 6.1,
        'cod': 3.5,
        'fish': 4.0,

        // Dairy (moderate-high)
        'cheese': 13.5,
        'butter': 11.9,
        'cream': 7.6,
        'milk': 3.2,
        'yogurt': 2.5,
        'eggs': 4.8,
        'ice cream': 6.0,

        // Plant proteins (low impact)
        'tofu': 2.0,
        'tempeh': 1.8,
        'lentils': 0.9,
        'chickpeas': 0.8,
        'beans': 0.7,
        'black beans': 0.7,
        'kidney beans': 0.7,
        'peas': 0.8,
        'peanuts': 1.3,
        'almonds': 2.3,
        'walnuts': 2.2,
        'cashews': 2.5,
        'seitan': 1.5,

        // Grains
        'rice': 2.7,
        'pasta': 1.8,
        'bread': 1.6,
        'wheat': 1.4,
        'oats': 1.6,
        'quinoa': 1.2,
        'couscous': 1.3,
        'flour': 1.4,

        // Vegetables (very low)
        'potatoes': 0.5,
        'tomatoes': 1.4,
        'onions': 0.4,
        'carrots': 0.4,
        'broccoli': 0.8,
        'spinach': 0.5,
        'lettuce': 0.7,
        'peppers': 1.0,
        'mushrooms': 0.6,
        'zucchini': 0.5,
        'eggplant': 0.6,
        'cabbage': 0.4,
        'cauliflower': 0.7,
        'kale': 0.5,
        'sweet potato': 0.5,
        'corn': 0.7,
        'avocado': 1.3,
        'cucumber': 0.4,
        'celery': 0.3,
        'garlic': 0.5,
        'ginger': 0.6,

        // Fruits
        'banana': 0.7,
        'apple': 0.4,
        'orange': 0.5,
        'berries': 1.1,
        'strawberries': 1.1,
        'grapes': 0.8,
        'mango': 1.0,
        'pineapple': 0.9,
        'lemon': 0.3,
        'lime': 0.3,
        'coconut': 1.0,

        // Oils & Condiments
        'olive oil': 3.5,
        'vegetable oil': 2.8,
        'coconut oil': 3.2,
        'soy sauce': 1.0,
        'sugar': 1.8,
        'honey': 1.2,
        'maple syrup': 1.1,
        'chocolate': 4.5,
        'cocoa': 4.5,

        // Beverages
        'coffee': 8.0,
        'tea': 1.2,

        // Plant milks
        'oat milk': 0.9,
        'soy milk': 1.0,
        'almond milk': 0.7,
        'coconut milk': 1.2,
    };

    // Nutritional data per 100g (simplified)
    const nutritionData = {
        'beef': { calories: 250, protein: 26, fiber: 0, iron: 2.6, vitaminC: 0, category: 'protein' },
        'chicken': { calories: 165, protein: 31, fiber: 0, iron: 1.0, vitaminC: 0, category: 'protein' },
        'pork': { calories: 242, protein: 27, fiber: 0, iron: 1.0, vitaminC: 0, category: 'protein' },
        'lamb': { calories: 294, protein: 25, fiber: 0, iron: 1.9, vitaminC: 0, category: 'protein' },
        'salmon': { calories: 208, protein: 20, fiber: 0, iron: 0.8, vitaminC: 0, category: 'protein' },
        'tofu': { calories: 144, protein: 15, fiber: 0.3, iron: 5.4, vitaminC: 0, category: 'protein' },
        'tempeh': { calories: 192, protein: 20, fiber: 7.0, iron: 2.7, vitaminC: 0, category: 'protein' },
        'lentils': { calories: 116, protein: 9, fiber: 8.0, iron: 3.3, vitaminC: 1.5, category: 'protein' },
        'chickpeas': { calories: 164, protein: 8.9, fiber: 7.6, iron: 2.9, vitaminC: 1.3, category: 'protein' },
        'beans': { calories: 127, protein: 8.7, fiber: 6.4, iron: 2.1, vitaminC: 0, category: 'protein' },
        'eggs': { calories: 155, protein: 13, fiber: 0, iron: 1.8, vitaminC: 0, category: 'protein' },
        'cheese': { calories: 402, protein: 25, fiber: 0, iron: 0.7, vitaminC: 0, category: 'dairy' },
        'rice': { calories: 130, protein: 2.7, fiber: 0.4, iron: 0.2, vitaminC: 0, category: 'grain' },
        'quinoa': { calories: 120, protein: 4.4, fiber: 2.8, iron: 1.5, vitaminC: 0, category: 'grain' },
        'broccoli': { calories: 34, protein: 2.8, fiber: 2.6, iron: 0.7, vitaminC: 89, category: 'vegetable' },
        'spinach': { calories: 23, protein: 2.9, fiber: 2.2, iron: 2.7, vitaminC: 28, category: 'vegetable' },
        'sweet potato': { calories: 86, protein: 1.6, fiber: 3.0, iron: 0.6, vitaminC: 2.4, category: 'vegetable' },
        'avocado': { calories: 160, protein: 2, fiber: 6.7, iron: 0.6, vitaminC: 10, category: 'vegetable' },
    };

    // Sustainable substitution suggestions
    const substitutions = {
        'beef': [
            { replacement: 'lentils', reason: 'Lentils provide excellent protein and fiber with 97% less carbon emissions than beef.' },
            { replacement: 'mushrooms', reason: 'Mushrooms offer a rich umami flavor similar to beef with 98% less carbon impact.' },
            { replacement: 'tempeh', reason: 'Tempeh has a meaty texture with 20g protein per 100g and 93% less emissions.' },
            { replacement: 'beans', reason: 'Beans are a hearty, affordable protein source with 97% fewer emissions.' },
            { replacement: 'tofu', reason: 'Tofu is versatile and absorbs flavors well, with 93% lower carbon footprint.' },
        ],
        'lamb': [
            { replacement: 'chickpeas', reason: 'Chickpeas provide satisfying texture and protein with 97% less emissions.' },
            { replacement: 'lentils', reason: 'Lentils can replicate the heartiness of lamb dishes with 96% carbon savings.' },
            { replacement: 'seitan', reason: 'Seitan offers a chewy, meat-like texture with 94% lower footprint.' },
        ],
        'pork': [
            { replacement: 'jackfruit', reason: 'Jackfruit has a pulled-pork-like texture and is very low impact.' },
            { replacement: 'tempeh', reason: 'Tempeh provides similar protein levels with 76% less emissions.' },
            { replacement: 'mushrooms', reason: 'Mushrooms provide savory umami flavor with 92% less carbon.' },
        ],
        'chicken': [
            { replacement: 'tofu', reason: 'Tofu is a versatile, lower-carbon protein alternative with 71% less emissions.' },
            { replacement: 'chickpeas', reason: 'Chickpeas work great in curries and salads, with 88% less carbon.' },
            { replacement: 'tempeh', reason: 'Tempeh offers comparable protein with a firm texture and 74% savings.' },
        ],
        'shrimp': [
            { replacement: 'hearts of palm', reason: 'Hearts of palm mimic shrimp texture with dramatically lower carbon footprint.' },
            { replacement: 'chickpeas', reason: 'Crispy roasted chickpeas can substitute in many shrimp dishes.' },
        ],
        'prawns': [
            { replacement: 'king oyster mushrooms', reason: 'Sliced king oyster mushrooms can mimic prawn texture beautifully.' },
        ],
        'cheese': [
            { replacement: 'nutritional yeast', reason: 'Nutritional yeast provides a cheesy flavor with 95% less emissions.' },
            { replacement: 'cashew cream', reason: 'Blended cashews create creamy sauces with 81% less carbon impact.' },
        ],
        'butter': [
            { replacement: 'olive oil', reason: 'Olive oil is heart-healthy and has 71% less carbon footprint than butter.' },
            { replacement: 'avocado', reason: 'Mashed avocado works as a spread with 89% less emissions.' },
        ],
        'cream': [
            { replacement: 'coconut cream', reason: 'Coconut cream offers richness with 84% less carbon impact.' },
            { replacement: 'cashew cream', reason: 'Blended cashews create a silky cream alternative.' },
        ],
        'milk': [
            { replacement: 'oat milk', reason: 'Oat milk has a creamy texture with 72% less emissions than dairy milk.' },
            { replacement: 'soy milk', reason: 'Soy milk matches dairy milk in protein with 69% less carbon.' },
        ],
        'rice': [
            { replacement: 'quinoa', reason: 'Quinoa has more protein and fiber with 56% less carbon than rice.' },
            { replacement: 'couscous', reason: 'Couscous cooks faster and has 52% less emissions.' },
        ],
        'bacon': [
            { replacement: 'smoked tempeh', reason: 'Smoked tempeh provides a smoky, savory flavor with far less carbon.' },
            { replacement: 'coconut bacon', reason: 'Toasted coconut flakes with liquid smoke create a crispy, smoky topping.' },
        ],
        'salmon': [
            { replacement: 'marinated tofu', reason: 'Marinated and baked tofu can mimic salmon texture with 63% less carbon.' },
        ],
        'eggs': [
            { replacement: 'flax eggs', reason: 'Ground flax + water works as a binder in baking with much lower impact.' },
            { replacement: 'tofu scramble', reason: 'Seasoned crumbled tofu makes a great scrambled egg substitute.' },
        ],
    };

    // Health benefit tags
    const healthBenefits = {
        'lentils': ['high fiber', 'iron-rich', 'heart healthy', 'low fat'],
        'chickpeas': ['high fiber', 'B vitamins', 'mineral-rich', 'blood sugar control'],
        'beans': ['high fiber', 'protein-rich', 'heart healthy', 'weight management'],
        'tofu': ['complete protein', 'calcium-rich', 'low calorie', 'isoflavones'],
        'tempeh': ['probiotics', 'high protein', 'bone health', 'B12 (fermented)'],
        'quinoa': ['complete protein', 'gluten-free', 'mineral-rich', 'high fiber'],
        'spinach': ['iron-rich', 'vitamin K', 'antioxidants', 'eye health'],
        'broccoli': ['vitamin C', 'cancer-fighting', 'fiber', 'vitamin K'],
        'sweet potato': ['vitamin A', 'antioxidants', 'fiber', 'blood sugar regulation'],
        'oats': ['cholesterol-lowering', 'fiber', 'sustained energy', 'B vitamins'],
        'mushrooms': ['vitamin D', 'immune support', 'low calorie', 'B vitamins'],
        'avocado': ['healthy fats', 'potassium', 'fiber', 'heart healthy'],
        'walnuts': ['omega-3', 'brain health', 'antioxidants', 'heart healthy'],
        'olive oil': ['monounsaturated fats', 'anti-inflammatory', 'heart healthy', 'antioxidants'],
    };

    // Sample recipes database
    const sampleRecipes = [
        {
            id: 1,
            name: 'Classic Beef Bolognese',
            ingredients: [
                { name: 'beef', amount: 500, unit: 'g' },
                { name: 'tomatoes', amount: 400, unit: 'g' },
                { name: 'onions', amount: 150, unit: 'g' },
                { name: 'garlic', amount: 10, unit: 'g' },
                { name: 'olive oil', amount: 30, unit: 'ml' },
                { name: 'pasta', amount: 400, unit: 'g' },
                { name: 'cheese', amount: 50, unit: 'g' },
            ],
            servings: 4,
            cuisine: 'Italian',
            time: '45 min',
        },
        {
            id: 2,
            name: 'Chicken Stir-Fry',
            ingredients: [
                { name: 'chicken', amount: 400, unit: 'g' },
                { name: 'rice', amount: 300, unit: 'g' },
                { name: 'broccoli', amount: 200, unit: 'g' },
                { name: 'peppers', amount: 150, unit: 'g' },
                { name: 'soy sauce', amount: 30, unit: 'ml' },
                { name: 'garlic', amount: 10, unit: 'g' },
                { name: 'ginger', amount: 10, unit: 'g' },
                { name: 'vegetable oil', amount: 20, unit: 'ml' },
            ],
            servings: 3,
            cuisine: 'Asian',
            time: '25 min',
        },
        {
            id: 3,
            name: 'Lamb Curry',
            ingredients: [
                { name: 'lamb', amount: 500, unit: 'g' },
                { name: 'onions', amount: 200, unit: 'g' },
                { name: 'tomatoes', amount: 300, unit: 'g' },
                { name: 'garlic', amount: 15, unit: 'g' },
                { name: 'ginger', amount: 15, unit: 'g' },
                { name: 'cream', amount: 100, unit: 'ml' },
                { name: 'rice', amount: 300, unit: 'g' },
            ],
            servings: 4,
            cuisine: 'Indian',
            time: '60 min',
        },
        {
            id: 4,
            name: 'Salmon with Buttered Vegetables',
            ingredients: [
                { name: 'salmon', amount: 400, unit: 'g' },
                { name: 'butter', amount: 40, unit: 'g' },
                { name: 'potatoes', amount: 400, unit: 'g' },
                { name: 'broccoli', amount: 200, unit: 'g' },
                { name: 'lemon', amount: 50, unit: 'g' },
                { name: 'garlic', amount: 10, unit: 'g' },
            ],
            servings: 2,
            cuisine: 'European',
            time: '35 min',
        },
        {
            id: 5,
            name: 'Bacon Cheeseburger',
            ingredients: [
                { name: 'beef', amount: 400, unit: 'g' },
                { name: 'bacon', amount: 100, unit: 'g' },
                { name: 'cheese', amount: 80, unit: 'g' },
                { name: 'bread', amount: 200, unit: 'g' },
                { name: 'lettuce', amount: 50, unit: 'g' },
                { name: 'tomatoes', amount: 100, unit: 'g' },
                { name: 'onions', amount: 50, unit: 'g' },
            ],
            servings: 4,
            cuisine: 'American',
            time: '20 min',
        },
        {
            id: 6,
            name: 'Vegetable Lentil Soup',
            ingredients: [
                { name: 'lentils', amount: 300, unit: 'g' },
                { name: 'carrots', amount: 200, unit: 'g' },
                { name: 'onions', amount: 150, unit: 'g' },
                { name: 'celery', amount: 100, unit: 'g' },
                { name: 'tomatoes', amount: 200, unit: 'g' },
                { name: 'garlic', amount: 10, unit: 'g' },
                { name: 'olive oil', amount: 20, unit: 'ml' },
                { name: 'spinach', amount: 100, unit: 'g' },
            ],
            servings: 4,
            cuisine: 'Mediterranean',
            time: '40 min',
        },
    ];

    // Calculate carbon footprint for a recipe
    function calculateRecipeCO2(ingredients) {
        let totalCO2 = 0;
        ingredients.forEach(ing => {
            const name = ing.name.toLowerCase();
            const kgAmount = ing.amount / 1000;
            const co2PerKg = carbonFootprint[name] || 1.0;
            totalCO2 += co2PerKg * kgAmount;
        });
        return Math.round(totalCO2 * 100) / 100;
    }

    // Get carbon rating (A-E scale)
    function getCarbonRating(co2PerServing) {
        if (co2PerServing < 0.5) return { grade: 'A', label: 'Very Low', color: '#2d6a4f' };
        if (co2PerServing < 1.0) return { grade: 'B', label: 'Low', color: '#52b788' };
        if (co2PerServing < 2.0) return { grade: 'C', label: 'Moderate', color: '#f4a261' };
        if (co2PerServing < 4.0) return { grade: 'D', label: 'High', color: '#e76f51' };
        return { grade: 'E', label: 'Very High', color: '#d62828' };
    }

    // Find high-impact ingredients that can be substituted
    function findSubstitutableIngredients(ingredients) {
        const results = [];
        ingredients.forEach(ing => {
            const name = ing.name.toLowerCase();
            if (substitutions[name]) {
                const co2 = (carbonFootprint[name] || 0) * (ing.amount / 1000);
                results.push({
                    ingredient: name,
                    amount: ing.amount,
                    unit: ing.unit,
                    co2: co2,
                    co2PerKg: carbonFootprint[name] || 0,
                    alternatives: substitutions[name],
                });
            }
        });
        // Sort by carbon impact (highest first)
        results.sort((a, b) => b.co2 - a.co2);
        return results;
    }

    // Calculate carbon savings from a substitution
    function calculateSavings(originalIngredient, replacementName, amountKg) {
        const originalCO2 = (carbonFootprint[originalIngredient] || 1.0) * amountKg;
        const replacementCO2 = (carbonFootprint[replacementName] || 1.0) * amountKg;
        const savings = originalCO2 - replacementCO2;
        const percentage = Math.round((savings / originalCO2) * 100);
        return {
            originalCO2: Math.round(originalCO2 * 100) / 100,
            replacementCO2: Math.round(replacementCO2 * 100) / 100,
            savingsKg: Math.round(savings * 100) / 100,
            savingsPercent: percentage,
        };
    }

    // Get fun equivalence for CO2 savings
    function getCO2Equivalence(savingsKg) {
        // Average car emits ~0.21 kg CO2 per km
        const kmDriving = Math.round(savingsKg / 0.21 * 10) / 10;
        // Average tree absorbs ~22 kg CO2 per year = ~0.06 kg per day
        const treeDays = Math.round(savingsKg / 0.06 * 10) / 10;
        // Average phone charge = ~0.005 kg CO2
        const phoneCharges = Math.round(savingsKg / 0.005);

        const equivalences = [];
        if (kmDriving >= 0.1) equivalences.push(`${kmDriving} km of driving`);
        if (treeDays >= 0.1) equivalences.push(`what a tree absorbs in ${treeDays} days`);
        if (phoneCharges >= 1) equivalences.push(`${phoneCharges} phone charges`);
        return equivalences;
    }

    return {
        carbonFootprint,
        nutritionData,
        substitutions,
        healthBenefits,
        sampleRecipes,
        calculateRecipeCO2,
        getCarbonRating,
        findSubstitutableIngredients,
        calculateSavings,
        getCO2Equivalence,
    };
})();
