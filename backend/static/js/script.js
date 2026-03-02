(function(){
/**
 * Main Application Script - MealMaker Frontend
 * Handles fridge management, inventory editing, and recipe filtering across multiple pages
 */

// === UTILITY FUNCTIONS ===

/**
 * Initialize fridges in localStorage if they don't exist.
 * Creates 3 default fridge slots with empty inventories.
 */
function initializeFridges() {
    if (!localStorage.getItem("fridges")) {
        const defaultFridges = Array.from({ length: 3 }, (_, i) => ({
            name: `Fridge Slot ${i + 1}`,
            items: {}
        }));
        localStorage.setItem("fridges", JSON.stringify(defaultFridges));
    }
}

/**
 * Retrieve all fridges from localStorage.
 * @returns {Array} Array of fridge objects with name and items
 */
function getFridges() {
    return JSON.parse(localStorage.getItem("fridges"));
}

/**
 * Save all fridges to localStorage.
 * @param {Array} fridges - Array of fridge objects to persist
 */
function saveFridges(fridges) {
    localStorage.setItem("fridges", JSON.stringify(fridges));
}

// ------------------------------------
// EDIT FRIDGE PAGE LOGIC
// ------------------------------------

/**
 * Setup and initialize the edit fridge page.
 * Allows users to manually add/edit/delete items in a specific fridge.
 */
function setupEditPage() {
    initializeFridges();

    // Get fridge index from URL parameter (?slot=1)
    const urlParams = new URLSearchParams(window.location.search);
    const slotIndex = parseInt(urlParams.get("slot")) - 1;

    const fridges = getFridges();
    const fridge = fridges[slotIndex];

    const fridgeNameEl = document.querySelector(".fridge-name");
    const itemList = document.getElementById("itemList");
    const addItemBtn = document.getElementById("addItemBtn");

    // Display fridge name
    fridgeNameEl.textContent = fridge.name;

    // Save fridge name when edited
    fridgeNameEl.addEventListener("blur", () => {
        fridge.name = fridgeNameEl.textContent.trim();
        saveFridges(fridges);
    });

    /**
     * Render all items in the fridge to the UI.
     */
    function renderItems() {
        itemList.innerHTML = "";

        // Create list item for each inventory entry
        for (const [name, qty] of Object.entries(fridge.items)) {
            const li = document.createElement("li");
            li.classList.add("item");
            li.dataset.origName = name;
            li.innerHTML = `
                <span class="item-name" contenteditable="true">${name}</span>
                <span class="item-qty" contenteditable="true">${qty}</span>
                <button class="delete-btn">×</button>
            `;

            attachItemHandlers(li);
            itemList.appendChild(li);
        }
    }

    /**
     * Attach event handlers to item edit/delete controls.
     * @param {Element} li - The list item element
     * @param {string} originalName - The original ingredient name
     */
    function attachItemHandlers(li) {
        const nameEl = li.querySelector(".item-name");
        const qtyEl = li.querySelector(".item-qty");
        const deleteBtn = li.querySelector(".delete-btn");
        let originalName = li.dataset.origName;

        /**
         * Save item changes on blur (when user stops editing).
         */
        function saveItem() {
            const newName = nameEl.textContent.trim();
            const newQty = qtyEl.textContent.trim();

            // Remove old entry if name changed
            if (originalName !== newName) {
                delete fridge.items[originalName];
                originalName = newName;
                li.dataset.origName = newName;
            }
            fridge.items[newName] = newQty;

            saveFridges(fridges);
        }

        // Save on blur for both name and quantity
        nameEl.addEventListener("blur", saveItem);
        qtyEl.addEventListener("blur", saveItem);

        // Delete item when × button clicked
        deleteBtn.addEventListener("click", () => {
            delete fridge.items[originalName];
            saveFridges(fridges);
            renderItems();
        });
    }

    // Add new item button handler (generate unique placeholder name)
    addItemBtn.addEventListener("click", () => {
        let base = "New Item";
        let idx = 1;
        let key = base;
        while (fridge.items.hasOwnProperty(key)) {
            idx += 1;
            key = `${base} ${idx}`;
        }
        fridge.items[key] = "0";
        saveFridges(fridges);
        renderItems();
    });

    // Render initial items
    renderItems();
}

// === RECIPE SELECTION LOGIC ===

/**
 * Merge contents of multiple fridges into a single combined inventory.
 * Adds quantities of duplicate items and sorts alphabetically.
 * 
 * @param {Array<number>} indices - Array of fridge slot indices to merge
 * @returns {Object} Merged and sorted inventory dictionary
 */
function mergeSelectedFridges(indices) {
    const fridges = getFridges();
    let merged = {};

    // Merge contents of all selected fridges
    indices.forEach(i => {
        const items = fridges[i].items;
        for (const [name, qty] of Object.entries(items)) {
            if (!merged[name]) {
                merged[name] = qty;
            } else {
                // Add quantities if item exists in multiple fridges
                const num1 = parseFloat(merged[name]) || 0;
                const num2 = parseFloat(qty) || 0;
                merged[name] = (num1 + num2).toString();
            }
        }
    });

    // Sort keys alphabetically for consistent display
    const sortedKeys = quickSort(Object.keys(merged));
    let sortedMerged = {};
    sortedKeys.forEach(key => (sortedMerged[key] = merged[key]));

    return sortedMerged;
}

/**
 * QuickSort algorithm for alphabetical sorting.
 * Implements classic QuickSort with case-insensitive comparison.
 * 
 * @param {Array<string>} arr - Array of strings to sort
 * @returns {Array<string>} Sorted array
 */
function quickSort(arr) {
    if (arr.length <= 1) return arr;
    // Use last element as pivot
    const pivot = arr[arr.length - 1];
    const left = [];
    const right = [];
    // Partition into left (less than pivot) and right (greater)
    for (let i = 0; i < arr.length - 1; i++) {
        if (arr[i].toLowerCase() < pivot.toLowerCase()) {
            left.push(arr[i]);
        } else {
            right.push(arr[i]);
        }
    }
    // Recursively sort and combine
    return [...quickSort(left), pivot, quickSort(right)];
}

/**
 * Setup the index page with fridge selection and recipe filtering.
 * Handles fridge slot selection, recipe preference inputs, and navigation.
 */
function setupIndexPage() {
    initializeFridges();
    const fridges = getFridges();
    const fridgeSlotsContainer = document.getElementById("fridgeSlots");
    const addFridgeBtn = document.getElementById("addFridgeBtn");
    const getRecipesBtn = document.getElementById("getRecipesBtn");

    let selectedIndices = new Set(); // Track which fridges are selected

    /**
     * Update the "Get Recipes" button state based on selection.
     * Button is only enabled when at least one fridge is selected.
     */
    function updateButtonState() {
        if (selectedIndices.size > 0) {
            getRecipesBtn.disabled = false;
            getRecipesBtn.classList.add("enabled");
        } else {
            getRecipesBtn.disabled = true;
            getRecipesBtn.classList.remove("enabled");
        }
    }

    /**
     * Dynamically render all fridge slots based on current data.
     */
    function renderSlots() {
        fridgeSlotsContainer.innerHTML = "";
        
        fridges.forEach((fridge, index) => {
            const itemCount = Object.keys(fridge.items).length;
            
            // Create slot container
            const slotWrapper = document.createElement("div");
            slotWrapper.classList.add("slot-wrapper");
            
            // Create slot element
            const slot = document.createElement("a");
            slot.classList.add("slot");
            slot.href = `#`;
            
            const textEl = document.createElement("span");
            textEl.classList.add("slot-text");
            textEl.textContent = itemCount === 0 
                ? `${fridge.name} - Empty` 
                : `${fridge.name} - ${itemCount} items`;
            
            const menuEl = document.createElement("span");
            menuEl.classList.add("slot-menu");
            menuEl.textContent = "⋮";
            
            slot.appendChild(textEl);
            slot.appendChild(menuEl);
            
            // Create context menu
            const contextMenu = document.createElement("div");
            contextMenu.classList.add("slot-context-menu");
            
            const editOption = document.createElement("button");
            editOption.classList.add("context-option", "edit-option");
            editOption.textContent = "Edit";
            editOption.addEventListener("click", (e) => {
                e.stopPropagation();
                window.location.href = `/edit?slot=${index + 1}`;
            });
            
            const deleteOption = document.createElement("button");
            deleteOption.classList.add("context-option", "delete-option");
            deleteOption.textContent = "Delete";
            deleteOption.addEventListener("click", (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to delete "${fridge.name}" and all its contents?`)) {
                    fridges.splice(index, 1);
                    saveFridges(fridges);
                    renderSlots();
                }
            });
            
            contextMenu.appendChild(editOption);
            contextMenu.appendChild(deleteOption);
            
            // Menu button (⋮) - toggle context menu
            menuEl.addEventListener("click", (e) => {
                e.stopPropagation();
                // Close any other open menus
                document.querySelectorAll(".slot-context-menu").forEach(menu => {
                    if (menu !== contextMenu) menu.classList.remove("active");
                });
                contextMenu.classList.toggle("active");
            });

            // Slot click - toggle selection
            slot.addEventListener("click", (e) => {
                e.preventDefault();
                if (selectedIndices.has(index)) {
                    selectedIndices.delete(index);
                    slot.classList.remove("selected");
                } else {
                    selectedIndices.add(index);
                    slot.classList.add("selected");
                }
                updateButtonState();
            });
            
            slotWrapper.appendChild(slot);
            slotWrapper.appendChild(contextMenu);
            fridgeSlotsContainer.appendChild(slotWrapper);
        });
    }

    // Click listener to close context menus (attached once outside renderSlots)
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".slot-wrapper")) {
            document.querySelectorAll(".slot-context-menu").forEach(menu => {
                menu.classList.remove("active");
            });
        }
    });

    // Render initial slots
    renderSlots();
    addFridgeBtn.addEventListener("click", () => {
        const newFridge = {
            name: `Fridge Slot ${fridges.length + 1}`,
            items: {}
        };
        fridges.push(newFridge);
        saveFridges(fridges);
        renderSlots();
    });

    // Get Recipes button handler
    getRecipesBtn.addEventListener("click", () => {
        // Merge all selected fridge inventories
        const mergedFridge = mergeSelectedFridges([...selectedIndices]);

        // Collect user preference filters
        const preferences = {
            calorieMin: parseInt(document.getElementById("calorieMin").value) || 0,
            calorieMax: parseInt(document.getElementById("calorieMax").value) || 9999,
            protein: parseInt(document.getElementById("proteinMin").value) || 0
        };

        // Save to localStorage for recipes page to access
        localStorage.setItem("mergedFridge", JSON.stringify(mergedFridge));
        localStorage.setItem("preferences", JSON.stringify(preferences));

        // Navigate to recipes page
        window.location.href = "/recipes";
    });
}


// === AUTO-DETECT PAGE TYPE AND INITIALIZE ===

/**
 * Auto-detect which page is loaded and run appropriate setup function.
 * - index.html: setupIndexPage()
 * - edit_fridge.html: setupEditPage()
 */
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("fridgeSlots")) {
        setupIndexPage(); // Home page with fridge slots
    }
    if (document.querySelector(".fridge-name")) {
        setupEditPage(); // Edit fridge page
    }
});

/**
 * Refresh fridge display when returning to index page from another page.
 * Fires when page is restored from history (popstate).
 */
window.addEventListener("pageshow", () => {
    if (document.getElementById("fridgeSlots")) {
        setupIndexPage();
    }
});

/**
 * Update fridge display when localStorage changes in another tab/window.
 */
window.addEventListener("storage", () => {
    if (document.getElementById("fridgeSlots")) {
        setupIndexPage();
    }
});

})();
