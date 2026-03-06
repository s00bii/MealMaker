(function(){
/**
 * Main Application Script - MealMaker Frontend
 * Handles fridge management, inventory editing, and recipe filtering across multiple pages
 */

// === UTILITY FUNCTIONS ===

/**
 * Fetch all fridge items from the API.
 * @returns {Promise<Array>} Array of fridge items from API
 */
// === DATA ACCESS ===

/**
 * Fetch all fridge records from the backend.
 * Each record represents a single fridge row with an `items` JSON object.
 * @returns {Promise<Array>} Array of fridge objects from API
 */
async function getFridges() {
    try {
        const response = await apiFetch("/api/fridge", { method: "GET" });
        if (!response.ok) throw new Error("Failed to fetch fridges");
        return await response.json();
    } catch (e) {
        console.error("Error fetching fridges:", e);
        return [];
    }
}

/**
 * Save fridges by calling the API.
 * For new fridges: POST to /api/fridge
 * For updates: PUT to /api/fridge/<id>
 * @param {Array} fridges - Fridges to save
 */
async function saveFridges(fridges) {
    // This is now handled by individual API calls in the UI logic
    // POST for new fridges, PUT for updates
}

// ------------------------------------
// EDIT FRIDGE PAGE LOGIC
// ------------------------------------

/**
 * Setup and initialize the edit fridge page.
 * Allows users to manually add/edit/delete items in a specific fridge.
 */
async function setupEditPage() {
    // show loading overlay
    const loading = document.getElementById("loadingOverlay");
    if (loading) loading.style.display = "flex";

    // Ensure user is logged in
    await requireLogin();

    // Get fridge name from URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    let fridgeName = urlParams.get("fridge");

    // Fetch all fridges and find the one we are editing
    const fridges = await getFridges();
    let fridge = fridges.find(f => f.name === fridgeName);
    if (!fridge) {
        console.error("Fridge not found", fridgeName);
        // hide loading even if error
        if (loading) loading.style.display = "none";
        return;
    }
    // if a placeholder default row exists, treat as empty (shouldn't normally happen)
    if (fridge.name === "Default") {
        fridge.items = {};
    }

    const fridgeNameEl = document.querySelector(".fridge-name");
    const itemList = document.getElementById("itemList");
    const addItemBtn = document.getElementById("addItemBtn");

    fridgeNameEl.textContent = fridgeName || "Fridge";

    // enable renaming and persist it
    fridgeNameEl.addEventListener("blur", async () => {
        const newName = fridgeNameEl.textContent.trim();
        if (newName && newName !== fridge.name) {
            fridge.name = newName;
            try {
                await apiFetch(`/api/fridge/${fridge.id}`, {
                    method: "PUT",
                    body: JSON.stringify({ name: newName })
                });
                // update URL so reload will work
                const params = new URLSearchParams(window.location.search);
                params.set("fridge", newName);
                window.history.replaceState({}, "", `/edit?${params.toString()}`);
                fridgeName = newName;
            } catch (e) {
                console.error("Error renaming fridge", e);
            }
        }
    });

    // convert JSON-object items into array for editing
    let fridgeItems = [];
    if (fridge.items && typeof fridge.items === "object") {
        for (const [iname, iqty] of Object.entries(fridge.items)) {
            fridgeItems.push({ name: iname, quantity: iqty, unit: "" });
        }
    }

    function itemsToJson() {
        const obj = {};
        fridgeItems.forEach(it => {
            if (it.name) obj[it.name] = it.quantity;
        });
        return obj;
    }

    /**
     * Sort items by quantity (highest first).
     * Extracts numeric value and sorts descending.
     */
    function sortByQuantity() {
        fridgeItems.sort((a, b) => {
            const qtyA = parseFloat(a.quantity) || 0;
            const qtyB = parseFloat(b.quantity) || 0;
            return qtyB - qtyA; // descending (most to least)
        });
    }

    /**
     * Render all items in the fridge to the UI.
     */
    function renderItems() {
        sortByQuantity(); // sort before rendering
        itemList.innerHTML = "";
        fridgeItems.forEach((item, idx) => {
            const li = document.createElement("li");
            li.classList.add("item");
            li.dataset.index = idx;
            li.innerHTML = `
                <span class="item-name" contenteditable="true">${item.name}</span>
                <span class="item-qty" contenteditable="true">${item.quantity}</span>
                <button class="delete-btn">×</button>
            `;
            attachItemHandlers(li, item, idx);
            itemList.appendChild(li);
        });
    }

    function attachItemHandlers(li, item, idx) {
        const nameEl = li.querySelector(".item-name");
        const qtyEl = li.querySelector(".item-qty");
        const deleteBtn = li.querySelector(".delete-btn");

        async function persistChanges() {
            try {
                // patch the fridge row with updated items JSON
                await apiFetch(`/api/fridge/${fridge.id}`, {
                    method: "PUT",
                    body: JSON.stringify({ items: itemsToJson() })
                });
            } catch (e) {
                console.error("Error updating fridge items", e);
            }
        }

        nameEl.addEventListener("blur", () => {
            item.name = nameEl.textContent.trim();
            persistChanges();
        });
        qtyEl.addEventListener("blur", () => {
            item.quantity = qtyEl.textContent.trim();
            persistChanges();
        });

        deleteBtn.addEventListener("click", async () => {
            fridgeItems.splice(idx, 1);
            renderItems();
            await persistChanges();
        });
    }

    addItemBtn.addEventListener("click", async () => {
        fridgeItems.push({ name: "New Item", quantity: "0", unit: "" });
        renderItems();
        try {
            await apiFetch(`/api/fridge/${fridge.id}`, {
                method: "PUT",
                body: JSON.stringify({ items: itemsToJson() })
            });
        } catch (e) {
            console.error("Error adding item to fridge", e);
        }
    });

    renderItems();
    if (loading) loading.style.display = "none";
}

// === RECIPE SELECTION LOGIC ===

/**
 * Merge contents of multiple items into a single combined inventory.
 * Used for recipe matching when multiple fridges are selected.
 * 
 * @param {Array<Object>} items - Array of item objects to merge
 * @returns {Object} Merged inventory dictionary
 */
function mergeItems(items) {
    let merged = {};

    items.forEach(item => {
        // Handle both array format {name, quantity} and object format {ingredient: qty}
        if (item.name) {
            // API format: {name, quantity}
            const key = item.name.toLowerCase();
            const num1 = parseFloat(merged[key]) || 0;
            const num2 = parseFloat(item.quantity) || 0;
            merged[key] = (num1 + num2).toString();
        } else {
            // Object format: {"Bread": "10", "Egg": "3"}
            Object.entries(item).forEach(([name, qty]) => {
                const key = name.toLowerCase();
                const num1 = parseFloat(merged[key]) || 0;
                const num2 = parseFloat(qty) || 0;
                merged[key] = (num1 + num2).toString();
            });
        }
    });

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
async function setupIndexPage() {
    // Ensure user is logged in first
    await requireLogin();
    
    const fridgeSlotsContainer = document.getElementById("fridgeSlots");
    const addFridgeBtn = document.getElementById("addFridgeBtn");
    const getRecipesBtn = document.getElementById("getRecipesBtn");
    // hide container until we have real data to avoid flicker
    fridgeSlotsContainer.style.visibility = "hidden";

    // Fetch all fridges for the user and sort by slot_index
    let fridgesList = await getFridges();
    // drop any leftover default placeholder
    fridgesList = fridgesList.filter(f => f.name !== "Default");
    fridgesList.sort((a, b) => (a.slot_index || 0) - (b.slot_index || 0));

    let selectedFridges = new Set(); // store names of selected fridges

    /**
     * Update the "Get Recipes" button state based on selection.
     */
    function updateButtonState() {
        if (selectedFridges.size > 0) {
            getRecipesBtn.disabled = false;
            getRecipesBtn.classList.add("enabled");
        } else {
            getRecipesBtn.disabled = true;
            getRecipesBtn.classList.remove("enabled");
        }
    }

    /**
     * Render fridge slots based on the current fridgesList.
     */
    function renderSlots() {
        fridgeSlotsContainer.innerHTML = "";

        fridgesList.forEach((fridge, index) => {
            const itemCount = fridge.items ? Object.keys(fridge.items).length : 0;

            const slotWrapper = document.createElement("div");
            slotWrapper.classList.add("slot-wrapper");

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
                window.location.href = `/edit?fridge=${encodeURIComponent(fridge.name)}`;
            });
            
            const deleteOption = document.createElement("button");
            deleteOption.classList.add("context-option", "delete-option");
            deleteOption.textContent = "Delete";
            deleteOption.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to delete "${fridge.name}"?`)) {
                    try {
                        await apiFetch(`/api/fridge/${fridge.id}`, { method: "DELETE" });
                        // remove from local list and re-render
                        fridgesList = fridgesList.filter(f => f.id !== fridge.id);
                        renderSlots();
                    } catch (e) {
                        console.error("Error deleting fridge:", e);
                    }
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
                if (selectedFridges.has(fridge.name)) {
                    selectedFridges.delete(fridge.name);
                    slot.classList.remove("selected");
                } else {
                    selectedFridges.add(fridge.name);
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
    // now that real data is rendered, make container visible
    fridgeSlotsContainer.style.visibility = "";
    const loading = document.getElementById("loadingOverlay");
    if (loading) loading.style.display = "none";
    
    // guard against multiple listeners/requests
    if (!addFridgeBtn.dataset.listenerAttached) {
        addFridgeBtn.dataset.listenerAttached = "true";
        addFridgeBtn.addEventListener("click", async () => {
            addFridgeBtn.disabled = true;
            // slot index = max existing +1
            const slotIndex = (fridgesList.length > 0 ? Math.max(...fridgesList.map(f => f.slot_index || 0)) : 0) + 1;
            const fridgeName = `Fridge Slot ${slotIndex}`;
            try {
                const response = await apiFetch("/api/fridge", {
                    method: "POST",
                    body: JSON.stringify({
                        name: fridgeName,
                        slot_index: slotIndex,
                        items: {}  // Empty inventory
                    })
                });

                if (!response.ok) {
                    const text = await response.text();
                    console.error("Failed to create fridge:", response.status, text);
                    alert("Failed to create fridge: " + (text || response.status));
                } else {
                    // reload full list
                    fridgesList = await getFridges();
                    fridgesList.sort((a, b) => (a.slot_index || 0) - (b.slot_index || 0));
                    renderSlots();
                }
            } catch (e) {
                console.error("Error creating fridge:", e);
            } finally {
                addFridgeBtn.disabled = false;
            }
        });
    }
    //DEBUG
    
    // Get Recipes button handler
    getRecipesBtn.addEventListener("click", () => {
        console.log("fridgesList:", JSON.stringify(fridgesList));
        console.log("selectedFridges:", [...selectedFridges]);
        
        const selectedItems = fridgesList
            .filter(f => selectedFridges.has(f.name))
            .flatMap(f => f.items);
        
        console.log("selectedItems:", JSON.stringify(selectedItems));
        
        const mergedFridge = mergeItems(selectedItems);

        const preferences = {
            calorieMin: parseInt(document.getElementById("calorieMin").value) || 0,
            calorieMax: parseInt(document.getElementById("calorieMax").value) || 9999,
            protein: parseInt(document.getElementById("proteinMin").value) || 0
        };

        localStorage.setItem("mergedFridge", JSON.stringify(mergedFridge));
        localStorage.setItem("preferences", JSON.stringify(preferences));

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
    if (document.getElementById("fridgeSlots") && !indexInitialized) {
        indexInitialized = true;
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
let indexInitialized = false;

window.addEventListener("pageshow", (e) => {
    // only re-init on back/forward navigation
    if (e.persisted && document.getElementById("fridgeSlots")) {
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
