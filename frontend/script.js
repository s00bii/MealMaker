// Initialize fridges in localStorage if not present
function initializeFridges() {
    if (!localStorage.getItem("fridges")) {
        const defaultFridges = Array.from({ length: 5 }, (_, i) => ({
            name: `Fridge Slot ${i + 1}`,
            items: {}
        }));
        localStorage.setItem("fridges", JSON.stringify(defaultFridges));
    }
}

// Load fridges data
function getFridges() {
    return JSON.parse(localStorage.getItem("fridges"));
}

// Save fridges data
function saveFridges(fridges) {
    localStorage.setItem("fridges", JSON.stringify(fridges));
}

// ------------------------------------
// INDEX PAGE LOGIC
// ------------------------------------
function setupIndexPage() {
    initializeFridges();
    const fridges = getFridges();
    const slots = document.querySelectorAll(".slot");

    // Update each slot display
    slots.forEach((slot, index) => {
        const fridge = fridges[index];
        const itemCount = Object.keys(fridge.items).length;

        // Show "Empty" if no items
        slot.textContent =
            itemCount === 0
                ? `${fridge.name} - Empty`
                : `${fridge.name} - ${itemCount} items`;
    });
}

// ------------------------------------
// EDIT FRIDGE PAGE LOGIC
// ------------------------------------
function setupEditPage() {
    initializeFridges();

    // Get fridge index from URL (?slot=1)
    const urlParams = new URLSearchParams(window.location.search);
    const slotIndex = parseInt(urlParams.get("slot")) - 1;

    const fridges = getFridges();
    const fridge = fridges[slotIndex];

    const fridgeNameEl = document.querySelector(".fridge-name");
    const itemList = document.getElementById("itemList");
    const addItemBtn = document.getElementById("addItemBtn");

    // Load fridge name
    fridgeNameEl.textContent = fridge.name;

    // Save name when edited
    fridgeNameEl.addEventListener("blur", () => {
        fridge.name = fridgeNameEl.textContent.trim();
        saveFridges(fridges);
    });

    // Render items into the list
    function renderItems() {
        itemList.innerHTML = "";

        for (const [name, qty] of Object.entries(fridge.items)) {
            const li = document.createElement("li");
            li.classList.add("item");
            li.innerHTML = `
                <span class="item-name" contenteditable="true">${name}</span>
                <span class="item-qty" contenteditable="true">${qty}</span>
                <button class="delete-btn">×</button>
            `;

            attachItemHandlers(li, name);
            itemList.appendChild(li);
        }
    }

    // Attach handlers for editing/deleting items
    function attachItemHandlers(li, originalName) {
        const nameEl = li.querySelector(".item-name");
        const qtyEl = li.querySelector(".item-qty");
        const deleteBtn = li.querySelector(".delete-btn");

        // Save on blur
        function saveItem() {
            const newName = nameEl.textContent.trim();
            const newQty = qtyEl.textContent.trim();

            if (originalName !== newName) delete fridge.items[originalName];
            fridge.items[newName] = newQty;

            saveFridges(fridges);
            originalName = newName;
        }

        nameEl.addEventListener("blur", saveItem);
        qtyEl.addEventListener("blur", saveItem);

        // Delete item
        deleteBtn.addEventListener("click", () => {
            delete fridge.items[originalName];
            saveFridges(fridges);
            renderItems();
        });
    }

    // Add new item
    addItemBtn.addEventListener("click", () => {
        fridge.items["New Item"] = "0";
        saveFridges(fridges);
        renderItems();
    });

    renderItems();
}

// Merge and sort selected fridges
function mergeSelectedFridges(indices) {
    const fridges = getFridges();
    let merged = {};

    // Merge contents
    indices.forEach(i => {
        const items = fridges[i].items;
        for (const [name, qty] of Object.entries(items)) {
            if (!merged[name]) {
                merged[name] = qty;
            } else {
                const num1 = parseFloat(merged[name]) || 0;
                const num2 = parseFloat(qty) || 0;
                merged[name] = (num1 + num2).toString();
            }
        }
    });

    // Sort keys alphabetically
    const sortedKeys = quickSort(Object.keys(merged));
    let sortedMerged = {};
    sortedKeys.forEach(key => (sortedMerged[key] = merged[key]));

    return sortedMerged;
}

// QuickSort for alphabetical order
function quickSort(arr) {
    if (arr.length <= 1) return arr;
    const pivot = arr[arr.length - 1];
    const left = [];
    const right = [];
    for (let i = 0; i < arr.length - 1; i++) {
        if (arr[i].toLowerCase() < pivot.toLowerCase()) {
            left.push(arr[i]);
        } else {
            right.push(arr[i]);
        }
    }
    return [...quickSort(left), pivot, ...quickSort(right)];
}

// Update index page
function setupIndexPage() {
    initializeFridges();
    const fridges = getFridges();
    const slots = document.querySelectorAll(".slot");
    const getRecipesBtn = document.getElementById("getRecipesBtn");

    let selectedIndices = new Set();

    function updateButtonState() {
        if (selectedIndices.size > 0) {
            getRecipesBtn.disabled = false;
            getRecipesBtn.classList.add("enabled");
        } else {
            getRecipesBtn.disabled = true;
            getRecipesBtn.classList.remove("enabled");
        }
    }

    // Populate slots & handle selection
    slots.forEach((slot, index) => {
        const fridge = fridges[index];
        const itemCount = Object.keys(fridge.items).length;
        const textEl = slot.querySelector(".slot-text");
        const menuEl = slot.querySelector(".slot-menu");

        // Populate text
        textEl.textContent =
            itemCount === 0
                ? `${fridge.name} - Empty`
                : `${fridge.name} - ${itemCount} items`;

        // Clicking dots → Edit fridge
        menuEl.addEventListener("click", (e) => {
            e.stopPropagation(); // Prevent slot selection
            window.location.href = `edit_fridge.html?slot=${index + 1}`;
        });

        // Clicking slot → Toggle selection
        slot.addEventListener("click", (e) => {
            e.preventDefault(); // Prevent default link behavior
            if (selectedIndices.has(index)) {
                selectedIndices.delete(index);
                slot.classList.remove("selected");
            } else {
                selectedIndices.add(index);
                slot.classList.add("selected");
            }
            updateButtonState();
        });
    });


    // Handle "Get Recipes"
    getRecipesBtn.addEventListener("click", () => {
        const mergedFridge = mergeSelectedFridges([...selectedIndices]);

        // Get preferences
        const preferences = {
            calorieMin: parseInt(document.getElementById("calorieMin").value) || 0,
            calorieMax: parseInt(document.getElementById("calorieMax").value) || 9999,
            protein: parseInt(document.getElementById("proteinMin").value) || 0
        };

        // Save both fridge and preferences
        localStorage.setItem("mergedFridge", JSON.stringify(mergedFridge));
        localStorage.setItem("preferences", JSON.stringify(preferences));

        // Redirect to recipes page
        window.location.href = "recipes.html";
    });
}


// ------------------------------------
// AUTO-DETECT PAGE
// ------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".slot")) {
        setupIndexPage(); // index.html
    }
    if (document.querySelector(".fridge-name")) {
        setupEditPage(); // edit_fridge.html
    }
});

// Refresh fridge slots when returning to index.html
window.addEventListener("pageshow", () => {
    if (document.querySelector(".slot")) {
        setupIndexPage();
    }
});

window.addEventListener("storage", () => {
    if (document.querySelector(".slot")) {
        setupIndexPage();
    }
});
