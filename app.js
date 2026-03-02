/**
 * Eco-Nudge Negotiator — Main Application Logic
 * 
 * Handles:
 * - Navigation and view management
 * - Recipe rendering and analysis
 * - LLM integration (Ollama local AI) with fallback mode
 * - Negotiation/suggestion engine
 * - Impact tracking and gamification
 * - User preferences and persistence
 */

const App = (() => {
    // ===== State =====
    let state = {
        currentView: 'recipes',
        currentRecipe: null,
        currentIngredients: [],
        ollamaUrl: 'http://localhost:11434',
        model: 'qwen3:4b',
        ollamaConnected: false,
        nudgeIntensity: 3,
        focusAreas: { carbon: true, health: true, cost: false },
        dietaryRestrictions: [],
        allergies: '',
        impact: {
            totalCO2Saved: 0,
            mealsOptimized: 0,
            swapsMade: 0,
            streak: 0,
            lastActiveDate: null,
            history: [],
            weeklyData: [0, 0, 0, 0, 0, 0, 0],
        },
        chatHistory: [],
        recipeChatHistory: [],
        dismissedSuggestions: {}, // track user fatigue per ingredient
        userMood: 'neutral', // neutral, receptive, annoyed
        suggestionCount: 0,
        savedRecipes: [], // saved/modified recipes
    };

    // ===== Initialization =====
    function init() {
        loadState();
        setupNavigation();
        setupEventListeners();
        renderRecipeGrid();
        renderSavedRecipesView();
        renderImpactView();
        updateStreakBadge();
        checkStreak();
    }

    // ===== State Persistence =====
    function loadState() {
        try {
            const saved = localStorage.getItem('econudge_state');
            if (saved) {
                const parsed = JSON.parse(saved);
                state = { ...state, ...parsed };
            }
            // Load Ollama URL separately
            const url = localStorage.getItem('econudge_ollama_url');
            if (url) state.ollamaUrl = url;
            const model = localStorage.getItem('econudge_ollama_model');
            if (model) state.model = model;
        } catch (e) {
            console.warn('Failed to load state:', e);
        }
        // Check Ollama connection on load
        checkOllamaConnection();
    }

    function saveState() {
        try {
            const toSave = { ...state };
            delete toSave.ollamaConnected; // Runtime-only flag
            localStorage.setItem('econudge_state', JSON.stringify(toSave));
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    }

    async function checkOllamaConnection() {
        try {
            const resp = await fetch(`${state.ollamaUrl}/api/tags`, { method: 'GET' });
            if (resp.ok) {
                state.ollamaConnected = true;
                const data = await resp.json();
                console.log(`Ollama connected. Available models: ${data.models?.map(m => m.name).join(', ')}`);
                // Update assistant status
                const statusEl = document.querySelector('.assistant-status');
                if (statusEl) statusEl.textContent = `Connected to Ollama — using ${state.model}`;
            } else {
                state.ollamaConnected = false;
            }
        } catch (e) {
            state.ollamaConnected = false;
            console.warn('Ollama not reachable:', e.message);
        }
    }

    // ===== Navigation =====
    function setupNavigation() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.dataset.view;
                switchView(view);
            });
        });
    }

    function switchView(viewName) {
        state.currentView = viewName;

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        const activeLink = document.querySelector(`[data-view="${viewName}"]`);
        if (activeLink) activeLink.classList.add('active');

        // Update views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const activeView = document.getElementById(`view-${viewName}`);
        if (activeView) activeView.classList.add('active');
    }

    // ===== Event Listeners =====
    function setupEventListeners() {
        // Back button
        document.getElementById('backToRecipes').addEventListener('click', () => {
            switchView('recipes');
            hideRecipeNavLink();
            state.currentRecipe = null;
            state.currentIngredients = [];
        });

        // Analyze custom recipe
        document.getElementById('analyzeCustomBtn').addEventListener('click', analyzeCustomRecipe);

        // Apply/dismiss all
        document.getElementById('applyAllBtn').addEventListener('click', applyAllSuggestions);
        document.getElementById('dismissAllBtn').addEventListener('click', dismissAllSuggestions);

        // Recipe chat
        document.getElementById('recipeChatSend').addEventListener('click', sendRecipeChat);
        document.getElementById('recipeChatInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendRecipeChat();
        });

        // Main chat
        document.getElementById('mainChatSend').addEventListener('click', sendMainChat);
        document.getElementById('mainChatInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMainChat();
        });

        // Quick prompts
        document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('mainChatInput').value = btn.dataset.prompt;
                sendMainChat();
            });
        });

        // Save recipe
        document.getElementById('saveRecipeBtn').addEventListener('click', saveCurrentRecipe);

        // Settings
        document.getElementById('saveApiKey').addEventListener('click', saveApiSettings);
        document.getElementById('testOllamaBtn').addEventListener('click', testOllamaConnection);
        document.getElementById('saveDietPrefs').addEventListener('click', saveDietPreferences);
        document.getElementById('clearDataBtn').addEventListener('click', clearAllData);

        // Load settings into form
        loadSettingsToForm();
    }

    // ===== Recipe Grid =====
    function renderRecipeGrid() {
        const grid = document.getElementById('recipeGrid');
        grid.innerHTML = '';

        EcoData.sampleRecipes.forEach(recipe => {
            const totalCO2 = EcoData.calculateRecipeCO2(recipe.ingredients);
            const perServing = totalCO2 / recipe.servings;
            const rating = EcoData.getCarbonRating(perServing);
            const substitutable = EcoData.findSubstitutableIngredients(recipe.ingredients);

            const ingredientNames = recipe.ingredients.map(i => {
                const isSub = substitutable.find(s => s.ingredient === i.name.toLowerCase());
                if (isSub) {
                    return `<span class="highlight-ingredient">${i.name}</span>`;
                }
                return i.name;
            }).join(', ');

            const card = document.createElement('div');
            card.className = 'recipe-card';
            card.innerHTML = `
                ${recipe.image ? `<div class="recipe-card-image"><img src="${recipe.image}" alt="${recipe.name}" loading="lazy"></div>` : ''}
                <div class="recipe-card-body">
                    <div class="recipe-card-header">
                        <h3>${recipe.name}</h3>
                    </div>
                    <div class="recipe-card-meta">
                        <span>🍽️ ${recipe.servings} servings</span>
                        <span>⏱️ ${recipe.time}</span>
                        <span>🌍 ${recipe.cuisine}</span>
                    </div>
                    <div class="recipe-card-ingredients">${ingredientNames}</div>
                    <div class="recipe-card-footer">
                        <span class="co2-mini">🌿 ${perServing.toFixed(2)} kg CO₂e/serving</span>
                        ${substitutable.length > 0 ? `<span class="text-green text-sm font-bold">${substitutable.length} swap${substitutable.length > 1 ? 's' : ''} available</span>` : '<span class="text-green text-sm">Already eco-friendly!</span>'}
                    </div>
                </div>
            `;
            card.addEventListener('click', () => openRecipeDetail(recipe));
            grid.appendChild(card);
        });
    }

    // ===== Recipe Detail =====
    function openRecipeDetail(recipe) {
        state.currentRecipe = recipe;
        state.currentIngredients = [...recipe.ingredients];
        state.recipeChatHistory = [];
        state.suggestionCount = 0;

        renderDetailView();
        switchView('detail');
        showRecipeNavLink(recipe.name);
    }

    function showRecipeNavLink(name) {
        const link = document.getElementById('navRecipeLink');
        const nameSpan = document.getElementById('navRecipeName');
        if (link && nameSpan) {
            // Truncate long names for the nav
            nameSpan.textContent = name.length > 18 ? name.substring(0, 18) + '…' : name;
            link.style.display = '';
            link.title = name;
        }
    }

    function hideRecipeNavLink() {
        const link = document.getElementById('navRecipeLink');
        if (link) link.style.display = 'none';
    }

    function renderDetailView() {
        const recipe = state.currentRecipe;
        const ingredients = state.currentIngredients;

        document.getElementById('detailRecipeName').textContent = recipe.name;
        document.getElementById('detailMeta').innerHTML = `
            <span>🍽️ ${recipe.servings} servings</span>
            <span>⏱️ ${recipe.time}</span>
            <span>🌍 ${recipe.cuisine}</span>
        `;

        // Carbon score
        const totalCO2 = EcoData.calculateRecipeCO2(ingredients);
        const perServing = totalCO2 / recipe.servings;
        const rating = EcoData.getCarbonRating(perServing);

        const gradeEl = document.getElementById('carbonGrade');
        gradeEl.textContent = rating.grade;
        gradeEl.style.background = rating.color;

        const barPercent = Math.min((perServing / 5) * 100, 100);
        const bar = document.getElementById('carbonBar');
        bar.style.width = `${barPercent}%`;
        bar.style.background = rating.color;

        document.getElementById('carbonTotal').textContent = `${totalCO2.toFixed(2)} kg CO₂e total`;
        document.getElementById('carbonPerServing').textContent = `${perServing.toFixed(2)} kg CO₂e/serving`;

        // Ingredients
        renderIngredientList(ingredients);

        // Suggestions
        renderSuggestions(ingredients);

        // Initial recipe chat message
        renderRecipeChatMessages();
    }

    function renderIngredientList(ingredients) {
        const list = document.getElementById('ingredientList');
        list.innerHTML = '';

        ingredients.forEach(ing => {
            const co2PerKg = EcoData.carbonFootprint[ing.name.toLowerCase()] || 1.0;
            const co2 = co2PerKg * (ing.amount / 1000);
            let impactClass = 'low-impact';
            if (co2PerKg >= 10) impactClass = 'high-impact';
            else if (co2PerKg >= 4) impactClass = 'medium-impact';

            const item = document.createElement('div');
            item.className = `ingredient-item ${impactClass}`;
            item.innerHTML = `
                <span class="ingredient-name">${ing.amount}${ing.unit} ${ing.name}</span>
                <span class="ingredient-co2">${co2.toFixed(2)} kg CO₂e</span>
            `;
            list.appendChild(item);
        });
    }

    // ===== Suggestion / Negotiation Engine =====
    function renderSuggestions(ingredients) {
        const container = document.getElementById('suggestionsContainer');
        container.innerHTML = '';

        const substitutable = EcoData.findSubstitutableIngredients(ingredients);

        if (substitutable.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; padding:1.5rem; color:var(--gray-500);">
                    <p style="font-size:1.5rem; margin-bottom:0.5rem;">🎉</p>
                    <p>This recipe is already quite eco-friendly! Great choice.</p>
                </div>
            `;
            document.getElementById('applyAllBtn').style.display = 'none';
            document.getElementById('dismissAllBtn').style.display = 'none';
            return;
        }

        // Determine how many suggestions to show based on nudge intensity
        const maxSuggestions = Math.min(substitutable.length, state.nudgeIntensity);
        const toShow = substitutable.slice(0, maxSuggestions);

        // Adapt based on user mood
        let introMessage = "I found some eco-friendly alternatives for this recipe!";
        if (state.userMood === 'annoyed') {
            introMessage = "Just one small thought — no pressure at all!";
        } else if (state.suggestionCount > 3) {
            introMessage = "Here's a quick suggestion. Feel free to skip if you prefer.";
        }

        document.querySelector('.panel-subtitle').textContent = introMessage;

        toShow.forEach((sub, index) => {
            const alt = sub.alternatives[0]; // Primary suggestion
            const savings = EcoData.calculateSavings(sub.ingredient, alt.replacement, sub.amount / 1000);
            const healthBenefits = EcoData.healthBenefits[alt.replacement] || [];

            const card = document.createElement('div');
            card.className = 'suggestion-card';
            card.dataset.ingredient = sub.ingredient;
            card.dataset.replacement = alt.replacement;
            card.style.animationDelay = `${index * 0.1}s`;

            let savingsTags = `
                <span class="savings-tag co2">🌿 -${savings.savingsKg.toFixed(2)} kg CO₂ (${savings.savingsPercent}%)</span>
            `;
            if (healthBenefits.length > 0) {
                savingsTags += `<span class="savings-tag health">❤️ ${healthBenefits[0]}</span>`;
            }

            // Adapt tone based on mood
            let reason = alt.reason;
            if (state.userMood === 'annoyed') {
                reason = `Just a thought: ${alt.replacement} could work here too. No worries if not!`;
            }

            card.innerHTML = `
                <div class="suggestion-header">
                    <span class="suggestion-swap">
                        ${capitalize(sub.ingredient)} <span class="arrow">→</span> ${capitalize(alt.replacement)}
                    </span>
                </div>
                <div class="suggestion-reason">${reason}</div>
                <div class="suggestion-savings">${savingsTags}</div>
                <div class="suggestion-actions">
                    <button class="btn btn-accept btn-sm" onclick="App.acceptSuggestion(this, '${sub.ingredient}', '${alt.replacement}', ${sub.amount})">
                        ✅ Swap it!
                    </button>
                    <button class="btn btn-decline btn-sm" onclick="App.declineSuggestion(this, '${sub.ingredient}')">
                        No thanks
                    </button>
                </div>
            `;
            container.appendChild(card);
        });

        if (toShow.length > 0) {
            document.getElementById('applyAllBtn').style.display = 'flex';
            document.getElementById('dismissAllBtn').style.display = 'flex';
        }

        state.suggestionCount += toShow.length;
    }

    function acceptSuggestion(buttonEl, originalIngredient, replacement, amount) {
        const card = buttonEl.closest('.suggestion-card');
        card.classList.add('accepted');
        card.querySelector('.suggestion-actions').innerHTML = '<span class="text-green font-bold text-sm">✅ Swapped!</span>';

        // Update ingredients
        state.currentIngredients = state.currentIngredients.map(ing => {
            if (ing.name.toLowerCase() === originalIngredient.toLowerCase()) {
                return { ...ing, name: replacement };
            }
            return ing;
        });

        // Calculate and record savings
        const savings = EcoData.calculateSavings(originalIngredient, replacement, amount / 1000);
        recordSwap(originalIngredient, replacement, savings.savingsKg);

        // Re-render ingredient list and carbon score
        renderIngredientList(state.currentIngredients);
        updateCarbonScore();

        // Reset mood since user is engaging positively
        state.userMood = 'receptive';

        showToast(`Swapped ${originalIngredient} → ${replacement}! Saving ${savings.savingsKg.toFixed(2)} kg CO₂`, 'success');
    }

    function declineSuggestion(buttonEl, ingredient) {
        const card = buttonEl.closest('.suggestion-card');
        card.classList.add('declined');
        card.querySelector('.suggestion-actions').innerHTML = '<span class="text-gray text-sm">Keeping original</span>';

        // Track dismissals for this ingredient
        if (!state.dismissedSuggestions[ingredient]) {
            state.dismissedSuggestions[ingredient] = 0;
        }
        state.dismissedSuggestions[ingredient]++;

        // Adjust mood if too many dismissals
        const totalDismissals = Object.values(state.dismissedSuggestions).reduce((a, b) => a + b, 0);
        if (totalDismissals >= 3) {
            state.userMood = 'annoyed';
        }

        // After declining, offer a softer alternative if available
        const subs = EcoData.substitutions[ingredient];
        if (subs && subs.length > 1 && state.dismissedSuggestions[ingredient] < subs.length) {
            // Only offer if not too annoyed
            if (state.userMood !== 'annoyed') {
                const altIndex = state.dismissedSuggestions[ingredient];
                const alt = subs[altIndex];
                showToast(`How about ${alt.replacement} instead? ${alt.reason.split('.')[0]}.`, 'info');
            }
        }

        saveState();
    }

    function applyAllSuggestions() {
        document.querySelectorAll('.suggestion-card:not(.accepted):not(.declined)').forEach(card => {
            const acceptBtn = card.querySelector('.btn-accept');
            if (acceptBtn) acceptBtn.click();
        });
    }

    function dismissAllSuggestions() {
        document.querySelectorAll('.suggestion-card:not(.accepted):not(.declined)').forEach(card => {
            const declineBtn = card.querySelector('.btn-decline');
            if (declineBtn) declineBtn.click();
        });
        showToast("No problem! Your recipe stays as is. 🍽️", 'info');
    }

    function updateCarbonScore() {
        const totalCO2 = EcoData.calculateRecipeCO2(state.currentIngredients);
        const perServing = totalCO2 / state.currentRecipe.servings;
        const rating = EcoData.getCarbonRating(perServing);

        const gradeEl = document.getElementById('carbonGrade');
        gradeEl.textContent = rating.grade;
        gradeEl.style.background = rating.color;

        const barPercent = Math.min((perServing / 5) * 100, 100);
        document.getElementById('carbonBar').style.width = `${barPercent}%`;
        document.getElementById('carbonBar').style.background = rating.color;

        document.getElementById('carbonTotal').textContent = `${totalCO2.toFixed(2)} kg CO₂e total`;
        document.getElementById('carbonPerServing').textContent = `${perServing.toFixed(2)} kg CO₂e/serving`;
    }

    // ===== Impact Tracking =====
    function recordSwap(original, replacement, savingsKg) {
        state.impact.totalCO2Saved += savingsKg;
        state.impact.swapsMade++;

        // Add to history
        state.impact.history.unshift({
            type: 'swap',
            original,
            replacement,
            savings: savingsKg,
            date: new Date().toISOString(),
            recipe: state.currentRecipe?.name || 'Custom Recipe',
        });

        // Update weekly data
        const dayIndex = new Date().getDay();
        const adjustedIndex = dayIndex === 0 ? 6 : dayIndex - 1; // Mon=0, Sun=6
        state.impact.weeklyData[adjustedIndex] += savingsKg;

        updateStreakBadge();
        saveState();
    }

    function recordMealOptimized() {
        state.impact.mealsOptimized++;
        checkStreak();
        saveState();
    }

    function checkStreak() {
        const today = new Date().toDateString();
        if (state.impact.lastActiveDate !== today) {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            if (state.impact.lastActiveDate === yesterday.toDateString()) {
                state.impact.streak++;
            } else if (state.impact.lastActiveDate !== null) {
                state.impact.streak = 1;
            } else {
                state.impact.streak = 1;
            }
            state.impact.lastActiveDate = today;
            saveState();
        }
    }

    function updateStreakBadge() {
        document.getElementById('streakBadge').textContent = `🔥 ${state.impact.streak}`;
    }

    function renderImpactView() {
        document.getElementById('totalCO2Saved').textContent = state.impact.totalCO2Saved.toFixed(2);
        document.getElementById('mealsOptimized').textContent = state.impact.mealsOptimized;
        document.getElementById('swapsMade').textContent = state.impact.swapsMade;
        document.getElementById('currentStreak').textContent = state.impact.streak;

        // CO2 equivalences
        const equivs = EcoData.getCO2Equivalence(state.impact.totalCO2Saved);
        document.getElementById('co2Equiv').textContent = equivs.length > 0 ? `≈ ${equivs[0]}` : '';

        // History list
        const historyList = document.getElementById('historyList');
        if (state.impact.history.length === 0) {
            historyList.innerHTML = '<div class="history-empty"><p>No eco-choices recorded yet. Start by analyzing a recipe!</p></div>';
        } else {
            historyList.innerHTML = '';
            state.impact.history.slice(0, 20).forEach(item => {
                const date = new Date(item.date);
                const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                const el = document.createElement('div');
                el.className = 'history-item';
                el.innerHTML = `
                    <span class="history-item-icon">🔄</span>
                    <span class="history-item-text">${capitalize(item.original)} → ${capitalize(item.replacement)} in ${item.recipe}</span>
                    <span class="history-item-savings">-${item.savings.toFixed(2)} kg</span>
                    <span class="history-item-date">${dateStr}</span>
                `;
                historyList.appendChild(el);
            });
        }

        // Weekly chart
        const maxVal = Math.max(...state.impact.weeklyData, 0.1);
        document.querySelectorAll('.chart-bar').forEach((bar, index) => {
            const percent = (state.impact.weeklyData[index] / maxVal) * 100;
            bar.style.height = `${Math.max(percent, 2)}%`;
        });
    }

    // ===== Saved Recipes =====
    function saveCurrentRecipe() {
        if (!state.currentRecipe) {
            showToast('No recipe is currently open.', 'warning');
            return;
        }

        const recipe = {
            id: Date.now(),
            name: state.currentRecipe.name,
            ingredients: JSON.parse(JSON.stringify(state.currentIngredients)),
            servings: state.currentRecipe.servings,
            cuisine: state.currentRecipe.cuisine || 'Custom',
            time: state.currentRecipe.time || 'N/A',
            savedAt: new Date().toISOString(),
        };

        state.savedRecipes.push(recipe);
        saveState();
        renderSavedRecipesView();
        showToast(`"${recipe.name}" saved to My Recipes!`, 'success');
    }

    function renderSavedRecipesView() {
        const grid = document.getElementById('savedRecipesGrid');
        const empty = document.getElementById('savedEmpty');
        if (!grid) return;

        // Clear previous cards (keep the empty placeholder)
        grid.querySelectorAll('.saved-recipe-card').forEach(c => c.remove());

        if (state.savedRecipes.length === 0) {
            if (empty) empty.style.display = '';
            return;
        }
        if (empty) empty.style.display = 'none';

        state.savedRecipes.forEach((recipe, idx) => {
            const totalCO2 = EcoData.calculateRecipeCO2(recipe.ingredients);
            const perServing = totalCO2 / recipe.servings;
            const rating = EcoData.getCarbonRating(perServing);
            const savedDate = new Date(recipe.savedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

            const card = document.createElement('div');
            card.className = 'saved-recipe-card';
            card.innerHTML = `
                <div class="saved-recipe-header">
                    <h3>${recipe.name}</h3>
                    <span class="carbon-badge" style="background:${rating.color}">${rating.grade}</span>
                </div>
                <div class="saved-recipe-meta">
                    <span>🍽️ ${recipe.servings} servings</span>
                    <span>🌍 ${recipe.cuisine}</span>
                    <span>🌿 ${perServing.toFixed(2)} kg CO₂e/serving</span>
                </div>
                <div class="saved-recipe-ingredients">
                    ${recipe.ingredients.map(i => `${i.amount}${i.unit} ${i.name}`).join(', ')}
                </div>
                <div class="saved-recipe-footer">
                    <span class="saved-recipe-date">Saved ${savedDate}</span>
                    <div class="saved-recipe-actions">
                        <button class="btn btn-sm btn-outline" onclick="App.openSavedRecipe(${idx})">Open</button>
                        <button class="btn btn-sm btn-danger-outline" onclick="App.deleteSavedRecipe(${idx})">🗑️</button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    function openSavedRecipe(index) {
        const recipe = state.savedRecipes[index];
        if (!recipe) return;
        openRecipeDetail({
            id: recipe.id,
            name: recipe.name,
            ingredients: JSON.parse(JSON.stringify(recipe.ingredients)),
            servings: recipe.servings,
            cuisine: recipe.cuisine,
            time: recipe.time,
        });
    }

    function deleteSavedRecipe(index) {
        const recipe = state.savedRecipes[index];
        if (!recipe) return;
        if (confirm(`Delete "${recipe.name}" from your saved recipes?`)) {
            state.savedRecipes.splice(index, 1);
            saveState();
            renderSavedRecipesView();
            showToast('Recipe deleted.', 'info');
        }
    }

    // ===== Custom Recipe Analysis =====
    function analyzeCustomRecipe() {
        const name = document.getElementById('customRecipeName').value.trim();
        const ingredientText = document.getElementById('customIngredients').value.trim();
        const servings = parseInt(document.getElementById('customServings').value) || 4;

        if (!name || !ingredientText) {
            showToast('Please enter a recipe name and ingredients.', 'warning');
            return;
        }

        const ingredients = parseIngredients(ingredientText);
        if (ingredients.length === 0) {
            showToast('Could not parse ingredients. Use format: 500g beef', 'warning');
            return;
        }

        const recipe = {
            id: Date.now(),
            name,
            ingredients,
            servings,
            cuisine: 'Custom',
            time: 'N/A',
        };

        openRecipeDetail(recipe);
        recordMealOptimized();
    }

    function parseIngredients(text) {
        const lines = text.split('\n').filter(l => l.trim());
        return lines.map(line => {
            const match = line.match(/(\d+)\s*(g|kg|ml|l|oz|cups?|tbsp|tsp)?\s+(.+)/i);
            if (match) {
                let amount = parseInt(match[1]);
                let unit = (match[2] || 'g').toLowerCase();
                const name = match[3].trim().toLowerCase();
                // Normalize to grams
                if (unit === 'kg') { amount *= 1000; unit = 'g'; }
                return { name, amount, unit };
            }
            // Fallback: just ingredient name
            return { name: line.trim().toLowerCase(), amount: 100, unit: 'g' };
        });
    }

    // ===== LLM Integration =====
    const SYSTEM_PROMPT = `You are Eco-Nudge, a friendly and empathetic sustainable meal planning assistant. Your role is to help users make eco-friendly food choices without being pushy or guilt-tripping. You run locally via Ollama, so user data stays private.

Core principles:
1. RESPECT USER AUTONOMY - Always present suggestions as options, never demands
2. BE TRANSPARENT - Explain the reasoning behind suggestions with data
3. BE EMPATHETIC - Acknowledge user preferences and emotional state
4. BE FACTUAL - Use real carbon footprint data and nutritional facts
5. AVOID GUILT-TRIPPING - Frame everything positively; focus on benefits, not blame
6. ADAPT YOUR TONE - If the user seems resistant, back off and be more gentle

You are a knowledgeable expert on sustainable food, nutrition, cooking techniques, meal planning, seasonal eating, food waste reduction, and dietary adaptations. Answer ANY food-related question the user has — you are not limited to substitutions only. You can:
- Discuss recipes, cooking techniques, meal prep strategies
- Explain the environmental impact of different foods and food systems
- Provide nutritional guidance and dietary information
- Suggest complete meal plans for different lifestyles
- Compare foods across carbon, health, cost, and taste dimensions
- Discuss food security, seasonal eating, and local sourcing
- Answer general questions while gently relating back to sustainability

Here is carbon footprint data you should reference (kg CO₂e per kg of food):
HIGH IMPACT: beef(27), lamb(24), shrimp(11.8), cheese(13.5), dark chocolate(18.7), coffee(16.5)
MODERATE: pork(7.6), chicken(6.9), farmed salmon(5.4), eggs(4.8), rice(2.7), pasta(1.8)
LOW IMPACT: tofu(2.0), lentils(0.9), beans(0.7), chickpeas(0.8), oats(0.5), potatoes(0.5), seasonal vegetables(0.3-1.4), fruits(0.4-1.1)

When suggesting alternatives:
- Explain the CO₂ savings clearly with specific numbers
- Mention health benefits when applicable
- Acknowledge that taste preferences matter
- Offer multiple options when possible
- If the user declines, gracefully accept and move on

Keep responses concise, warm, and helpful. Use emojis sparingly but appropriately. Format with markdown (bold, lists) for readability.`;

    async function callLLM(messages) {
        if (!state.ollamaConnected) {
            // Try to connect first
            await checkOllamaConnection();
        }

        if (!state.ollamaConnected) {
            return generateFallbackResponse(messages);
        }

        try {
            const response = await fetch(`${state.ollamaUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: state.model,
                    messages: [
                        { role: 'system', content: SYSTEM_PROMPT },
                        ...messages,
                    ],
                    stream: false,
                    options: {
                        temperature: 0.7,
                        num_predict: 300,
                    },
                    keep_alive: '10m',
                }),
            });

            if (!response.ok) {
                const errText = await response.text();
                console.error('Ollama API error:', errText);
                return generateFallbackResponse(messages);
            }

            const data = await response.json();
            return data.message?.content || generateFallbackResponse(messages);
        } catch (error) {
            console.error('Ollama call failed:', error);
            state.ollamaConnected = false;
            return generateFallbackResponse(messages);
        }
    }

    /**
     * Streaming LLM call — yields tokens as they arrive so the UI
     * can display them progressively for a perceived 1-2 s response time.
     * Falls back to a single non-streamed result when Ollama is unavailable.
     */
    async function callLLMStream(messages, onToken) {
        if (!state.ollamaConnected) {
            await checkOllamaConnection();
        }

        if (!state.ollamaConnected) {
            const fallback = generateFallbackResponse(messages);
            onToken(fallback, true);
            return fallback;
        }

        try {
            const response = await fetch(`${state.ollamaUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: state.model,
                    messages: [
                        { role: 'system', content: SYSTEM_PROMPT },
                        ...messages,
                    ],
                    stream: true,
                    options: {
                        temperature: 0.7,
                        num_predict: 300,
                    },
                    keep_alive: '10m',
                }),
            });

            if (!response.ok) {
                const errText = await response.text();
                console.error('Ollama API error:', errText);
                const fallback = generateFallbackResponse(messages);
                onToken(fallback, true);
                return fallback;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let full = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                // Each line is a JSON object
                for (const line of chunk.split('\n').filter(l => l.trim())) {
                    try {
                        const json = JSON.parse(line);
                        const token = json.message?.content || '';
                        full += token;
                        onToken(full, json.done === true);
                    } catch (_) { /* skip malformed */ }
                }
            }
            return full || generateFallbackResponse(messages);
        } catch (error) {
            console.error('Ollama stream failed:', error);
            state.ollamaConnected = false;
            const fallback = generateFallbackResponse(messages);
            onToken(fallback, true);
            return fallback;
        }
    }

    // Fallback responses when no API key is set
    function generateFallbackResponse(messages) {
        const lastMsg = messages[messages.length - 1].content.toLowerCase();

        // Recipe-specific context
        if (state.currentRecipe) {
            const substitutable = EcoData.findSubstitutableIngredients(state.currentIngredients);
            if (substitutable.length > 0) {
                const top = substitutable[0];
                const alt = top.alternatives[0];
                const savings = EcoData.calculateSavings(top.ingredient, alt.replacement, top.amount / 1000);
                return `Great question! Looking at your ${state.currentRecipe.name}, the biggest eco-opportunity is swapping **${top.ingredient}** (${top.co2PerKg} kg CO₂e/kg) for **${alt.replacement}**.\n\n${alt.reason}\n\nThis swap alone would save about **${savings.savingsKg.toFixed(2)} kg CO₂** — that's equivalent to ${EcoData.getCO2Equivalence(savings.savingsKg)[0] || 'a meaningful reduction'}!\n\nWould you like me to suggest how to adjust the recipe to make this work taste-wise? 🌿`;
            }
            return `Your ${state.currentRecipe.name} is already quite eco-friendly! The total carbon footprint is ${EcoData.calculateRecipeCO2(state.currentIngredients).toFixed(2)} kg CO₂e. Nice choice! 🌿`;
        }

        // General conversation responses
        if (lastMsg.includes('beef') || lastMsg.includes('alternative') || lastMsg.includes('substitute')) {
            return `Great question about beef alternatives! Here are my top picks:\n\n🌱 **Lentils** — Only 0.9 kg CO₂e/kg (vs beef at 27 kg). Rich in protein, iron, and fiber.\n🍄 **Mushrooms** — 0.6 kg CO₂e/kg. Amazing umami flavor that mimics meat.\n🫘 **Tempeh** — 1.8 kg CO₂e/kg. Fermented soy with 20g protein per 100g.\n🫛 **Chickpeas** — 0.8 kg CO₂e/kg. Versatile and satisfying.\n\nThe type of dish matters for choosing the right substitute. What are you planning to cook? 🍳`;
        }

        if (lastMsg.includes('carbon') || lastMsg.includes('footprint') || lastMsg.includes('impact')) {
            return `The carbon footprint of food varies enormously:\n\n🔴 **High impact**: Beef (27 kg CO₂e/kg), Lamb (24), Cheese (13.5), Shrimp (11.8)\n🟡 **Moderate**: Chicken (6.9), Pork (7.6), Salmon (5.4), Eggs (4.8)\n🟢 **Low impact**: Lentils (0.9), Beans (0.7), Tofu (2.0), Vegetables (0.3-1.4)\n\nSwapping just one beef meal per week for lentils saves about **1,300 kg CO₂ per year** — equivalent to driving 6,200 km less! 🚗💨\n\nWant me to analyze a specific recipe?`;
        }

        if (lastMsg.includes('dinner') || lastMsg.includes('meal') || lastMsg.includes('recipe') || lastMsg.includes('cook')) {
            return `Here are some delicious low-carbon dinner ideas:\n\n1. 🍲 **Lentil Bolognese** — All the hearty comfort, 90% less carbon than beef version\n2. 🥘 **Chickpea Curry** — Creamy, satisfying, and incredibly affordable\n3. 🍜 **Vegetable Stir-fry with Tofu** — Quick, nutritious, and versatile\n4. 🥗 **Quinoa Buddha Bowl** — Complete protein with roasted veggies\n5. 🍝 **Mushroom Pasta** — Rich umami flavor that rivals any meat sauce\n\nEach of these has a carbon footprint under 1 kg CO₂e per serving! Would you like a full recipe for any of these?`;
        }

        if (lastMsg.includes('cheese')) {
            return `Cheese has a surprisingly high carbon footprint — about **13.5 kg CO₂e per kg**, making it one of the highest-impact dairy products.\n\nThis is because it takes about 10 liters of milk to make 1 kg of cheese, concentrating the environmental impact.\n\nSome lower-impact alternatives:\n🧀 **Nutritional yeast** — Gives a cheesy flavor in pasta, popcorn, etc.\n🥜 **Cashew cream** — Makes wonderful creamy sauces\n\nThat said, cheese in moderation is fine! A small amount of parmesan goes a long way for flavor. Would you like tips on using less cheese while keeping great taste?`;
        }

        if (lastMsg.includes('pasta') || lastMsg.includes('spaghetti')) {
            return `Making pasta dishes more sustainable is easy and delicious!\n\nThe pasta itself (1.8 kg CO₂e/kg) is fairly moderate. The big differences come from:\n\n🔄 **Sauce choices**: Meat ragù → mushroom/lentil ragù saves ~10 kg CO₂\n🧀 **Cheese**: Use less, or try nutritional yeast for parmesan flavor\n🫒 **Base**: Olive oil-based sauces are lower impact than cream-based ones\n\nA simple aglio e olio (garlic & olive oil) is one of the lowest-carbon pastas you can make — and it's a classic Italian dish! 🇮🇹`;
        }

        return `I'd love to help with that! Here are a few things I can assist with:\n\n🥗 **Analyze a recipe** — I'll show the carbon footprint and suggest greener alternatives\n🔄 **Ingredient swaps** — Find eco-friendly replacements that taste great\n📊 **Impact tracking** — See how your choices add up over time\n💡 **Meal planning** — Get ideas for low-carbon, nutritious meals\n\nTry asking something like "What's a low-carbon dinner for 4?" or "Help me make my pasta greener!" 🌿`;
    }

    // ===== Chat Functions =====
    async function sendMainChat() {
        const input = document.getElementById('mainChatInput');
        const message = input.value.trim();
        if (!message) return;
        input.value = '';

        // Add user message
        state.chatHistory.push({ role: 'user', content: message });
        appendChatMessage('mainChatMessages', 'user', message);

        // Create a placeholder message for streaming
        const streamEl = appendStreamingMessage('mainChatMessages');

        // Stream LLM response
        const response = await callLLMStream(state.chatHistory, (text, done) => {
            updateStreamingMessage(streamEl, text, done);
        });

        state.chatHistory.push({ role: 'assistant', content: response });
    }

    async function sendRecipeChat() {
        const input = document.getElementById('recipeChatInput');
        const message = input.value.trim();
        if (!message) return;
        input.value = '';

        // Build context about current recipe
        const recipeContext = state.currentRecipe
            ? `Current recipe: ${state.currentRecipe.name}. Ingredients: ${state.currentIngredients.map(i => `${i.amount}${i.unit} ${i.name}`).join(', ')}. Total CO2: ${EcoData.calculateRecipeCO2(state.currentIngredients).toFixed(2)} kg CO₂e.`
            : '';

        state.recipeChatHistory.push({ role: 'user', content: `${recipeContext}\n\nUser question: ${message}` });
        appendChatMessage('recipeChatMessages', 'user', message);

        // Create a placeholder message for streaming
        const streamEl = appendStreamingMessage('recipeChatMessages');

        // Stream LLM response
        const response = await callLLMStream(state.recipeChatHistory, (text, done) => {
            updateStreamingMessage(streamEl, text, done);
        });

        state.recipeChatHistory.push({ role: 'assistant', content: response });
    }

    function appendChatMessage(containerId, role, content) {
        const container = document.getElementById(containerId);
        const msgEl = document.createElement('div');
        msgEl.className = `chat-message ${role}`;
        msgEl.innerHTML = `
            <div class="message-avatar">${role === 'assistant' ? '🌿' : '👤'}</div>
            <div class="message-content">${formatMarkdown(content)}</div>
        `;
        container.appendChild(msgEl);
        container.scrollTop = container.scrollHeight;
    }

    function appendChatLoading(containerId) {
        const container = document.getElementById(containerId);
        const id = 'loading-' + Date.now();
        const el = document.createElement('div');
        el.className = 'chat-message assistant';
        el.id = id;
        el.innerHTML = `
            <div class="message-avatar">🌿</div>
            <div class="message-content">
                <div class="message-loading">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    function removeChatLoading(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    /**
     * Append an empty assistant message element for streaming.
     * Returns the DOM element so it can be updated token-by-token.
     */
    function appendStreamingMessage(containerId) {
        const container = document.getElementById(containerId);
        const msgEl = document.createElement('div');
        msgEl.className = 'chat-message assistant';
        msgEl.innerHTML = `
            <div class="message-avatar">🌿</div>
            <div class="message-content streaming-cursor"></div>
        `;
        container.appendChild(msgEl);
        container.scrollTop = container.scrollHeight;
        return msgEl;
    }

    /**
     * Update a streaming message element with the latest accumulated text.
     * Removes the blinking cursor when done.
     */
    function updateStreamingMessage(msgEl, text, done) {
        const contentEl = msgEl.querySelector('.message-content');
        contentEl.innerHTML = formatMarkdown(text);
        if (done) {
            contentEl.classList.remove('streaming-cursor');
        }
        const container = msgEl.parentElement;
        container.scrollTop = container.scrollHeight;
    }

    function renderRecipeChatMessages() {
        const container = document.getElementById('recipeChatMessages');
        container.innerHTML = '';

        if (state.recipeChatHistory.length === 0) {
            // Add initial greeting
            const recipe = state.currentRecipe;
            const totalCO2 = EcoData.calculateRecipeCO2(state.currentIngredients);
            const rating = EcoData.getCarbonRating(totalCO2 / recipe.servings);

            let greeting = `I've analyzed your **${recipe.name}**. `;
            if (rating.grade === 'A' || rating.grade === 'B') {
                greeting += `This is already a great choice with a ${rating.label.toLowerCase()} carbon footprint! Ask me anything about it.`;
            } else {
                const subs = EcoData.findSubstitutableIngredients(state.currentIngredients);
                greeting += `It has a ${rating.label.toLowerCase()} carbon footprint (${totalCO2.toFixed(1)} kg CO₂e). `;
                if (subs.length > 0) {
                    greeting += `Check out the suggestions on the left — or ask me for more ideas!`;
                }
            }
            appendChatMessage('recipeChatMessages', 'assistant', greeting);
        } else {
            state.recipeChatHistory.forEach(msg => {
                appendChatMessage('recipeChatMessages', msg.role, msg.content);
            });
        }
    }

    // ===== Settings =====
    function loadSettingsToForm() {
        document.getElementById('ollamaUrlInput').value = state.ollamaUrl;
        // Set model dropdown or custom field
        const modelSelect = document.getElementById('modelSelect');
        const customModelInput = document.getElementById('customModelInput');
        const dropdownValues = [...modelSelect.options].map(o => o.value);
        if (dropdownValues.includes(state.model)) {
            modelSelect.value = state.model;
            customModelInput.value = '';
        } else {
            modelSelect.value = dropdownValues[0]; // default
            customModelInput.value = state.model;
        }
        document.getElementById('nudgeIntensity').value = state.nudgeIntensity;
        document.getElementById('focusCarbon').checked = state.focusAreas.carbon;
        document.getElementById('focusHealth').checked = state.focusAreas.health;
        document.getElementById('focusCost').checked = state.focusAreas.cost;
        document.getElementById('allergies').value = state.allergies || '';
    }

    function saveApiSettings() {
        state.ollamaUrl = document.getElementById('ollamaUrlInput').value.trim() || 'http://localhost:11434';
        localStorage.setItem('econudge_ollama_url', state.ollamaUrl);

        const customModel = document.getElementById('customModelInput').value.trim();
        state.model = customModel || document.getElementById('modelSelect').value;
        localStorage.setItem('econudge_ollama_model', state.model);

        saveState();
        showToast(`AI settings saved! Model: ${state.model}`, 'success');

        // Re-check connection with new settings
        checkOllamaConnection();
    }

    async function testOllamaConnection() {
        showToast('Testing connection to Ollama...', 'info');
        try {
            const resp = await fetch(`${state.ollamaUrl}/api/tags`, { method: 'GET' });
            if (resp.ok) {
                const data = await resp.json();
                const modelNames = data.models?.map(m => m.name) || [];
                state.ollamaConnected = true;
                const hasModel = modelNames.some(n => n.startsWith(state.model.split(':')[0]));
                let msg = `Connected! Found ${modelNames.length} model(s): ${modelNames.join(', ')}.`;
                if (!hasModel) {
                    msg += ` \n⚠️ Model "${state.model}" not found. Run: ollama pull ${state.model}`;
                    showToast(msg, 'warning');
                } else {
                    showToast(msg, 'success');
                }
                // Update assistant status
                const statusEl = document.querySelector('.assistant-status');
                if (statusEl) statusEl.textContent = `Connected to Ollama — using ${state.model}`;
            } else {
                state.ollamaConnected = false;
                showToast('Ollama responded with an error. Is it running?', 'error');
            }
        } catch (e) {
            state.ollamaConnected = false;
            showToast('Cannot reach Ollama. Make sure it is running on ' + state.ollamaUrl, 'error');
        }
    }

    function saveDietPreferences() {
        state.focusAreas.carbon = document.getElementById('focusCarbon').checked;
        state.focusAreas.health = document.getElementById('focusHealth').checked;
        state.focusAreas.cost = document.getElementById('focusCost').checked;
        state.nudgeIntensity = parseInt(document.getElementById('nudgeIntensity').value);
        state.allergies = document.getElementById('allergies').value.trim();

        state.dietaryRestrictions = [];
        if (document.getElementById('dietVegetarian').checked) state.dietaryRestrictions.push('vegetarian');
        if (document.getElementById('dietVegan').checked) state.dietaryRestrictions.push('vegan');
        if (document.getElementById('dietGlutenFree').checked) state.dietaryRestrictions.push('gluten-free');
        if (document.getElementById('dietDairyFree').checked) state.dietaryRestrictions.push('dairy-free');
        if (document.getElementById('dietNutFree').checked) state.dietaryRestrictions.push('nut-free');

        saveState();
        showToast('Dietary preferences saved!', 'success');
    }

    function clearAllData() {
        if (confirm('This will clear all your saved data, including impact history and preferences. Continue?')) {
            localStorage.removeItem('econudge_state');
            localStorage.removeItem('econudge_ollama_url');
            localStorage.removeItem('econudge_ollama_model');
            location.reload();
        }
    }

    // ===== Utilities =====
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function formatMarkdown(text) {
        // Simple markdown: bold, italic, lists, line breaks
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/^\- (.+)$/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const icons = { success: '✅', info: 'ℹ️', warning: '⚠️', error: '❌' };
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-text">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            if (toast.parentElement) toast.remove();
        }, 5000);
    }

    // ===== Public API =====
    return {
        init,
        acceptSuggestion,
        declineSuggestion,
        openSavedRecipe,
        deleteSavedRecipe,
    };
})();

// Initialize on load
document.addEventListener('DOMContentLoaded', App.init);
