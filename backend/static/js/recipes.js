(function(){
/**
 * Recipes Page Script - Display matching recipes
 * Fetches recipes from backend based on merged fridge inventory and user preferences
 */

/**
 * Load and display recipes when page loads.
 * Retrieves merged fridge data and preferences from localStorage,
 * calls backend API to get matching recipes, and renders them as cards.
 */
document.addEventListener("DOMContentLoaded", () => {
    const recipesContainer = document.getElementById("recipesContainer");

    // Retrieve merged fridge data and user preferences from localStorage
    const mergedFridge = JSON.parse(localStorage.getItem("mergedFridge")) || {};
    const preferences = JSON.parse(localStorage.getItem("preferences")) || {};

    // Check if we have fridge data
    if (Object.keys(mergedFridge).length === 0) {
        recipesContainer.innerHTML = "<p>No fridge data found. Go back and select fridges.</p>";
        return;
    }

    // Call backend API to get recipes matching the fridge ingredients and preferences
    fetch(`${window.location.origin}/get_recipes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fridge: mergedFridge, preferences: preferences })
    })
    .then(res => {
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        return res.json();
    })
    .then(data => {
        recipesContainer.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            recipesContainer.innerHTML = "<p>No matching recipes found. Try adjusting your preferences or add more ingredients.</p>";
            return;
        }

        data.forEach(recipe => {
            const div = document.createElement("div");
            div.classList.add("recipe-card");
            div.innerHTML = `
                <div class="recipe-title">${recipe.name}</div>
                <div class="recipe-meta">Calories: ${recipe.calories} | Protein: ${recipe.protein_g}g</div>
                <a class="recipe-link" href="${recipe.source_url}" target="_blank">View Recipe</a>
            `;
            recipesContainer.appendChild(div);
        });
    })
    .catch(() => {
        recipesContainer.innerHTML = "<p>Error loading recipes. Please try again.</p>";
    });
});

})();