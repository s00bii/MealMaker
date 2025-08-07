document.addEventListener("DOMContentLoaded", () => {
    const recipesContainer = document.getElementById("recipesContainer");

    // Load merged fridge data and preferences
    const mergedFridge = JSON.parse(localStorage.getItem("mergedFridge")) || {};
    const preferences = JSON.parse(localStorage.getItem("preferences")) || {};

    if (Object.keys(mergedFridge).length === 0) {
        recipesContainer.innerHTML = "<p>No fridge data found. Go back and select fridges.</p>";
        return;
    }

    // Call backend API
    fetch("http://127.0.0.1:5000/get_recipes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fridge: mergedFridge, preferences: preferences })
    })
    .then(res => res.json())
    .then(data => {
        recipesContainer.innerHTML = ""; // Clear loading text

        if (data.length === 0) {
            recipesContainer.innerHTML = "<p>No matching recipes found.</p>";
            return;
        }

        // Display recipe cards
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
    .catch(err => {
        recipesContainer.innerHTML = "<p>Error loading recipes. Check server.</p>";
        console.error(err);
    });
});