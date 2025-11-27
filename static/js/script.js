/// Modal functions
function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";

  // Clear previous results and inputs when opening modals
  if (modalId === "sellProductModal") {
    document.getElementById("sellResults").innerHTML = "";
    document.getElementById("sellProductSearch").value = "";
    document.getElementById("sellQuantity").value = "";
  } else if (modalId === "clinicProductModal") {
    document.getElementById("clinicResults").innerHTML = "";
    document.getElementById("clinicProductSearch").value = "";
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
  clearForms();
}

function clearForms() {
  // Optional chaining (?) ensures no error if the form element doesn't exist on the current page
  document.getElementById("addProductForm")?.reset();
  document.getElementById("sellProductForm")?.reset();
  document.getElementById("clinicProductForm")?.reset();
  document.getElementById("sellResults").innerHTML = "";
  document.getElementById("clinicResults").innerHTML = "";
}

// Close modal when clicking outside
window.onclick = function (event) {
  const modals = document.getElementsByClassName("modal");
  for (let modal of modals) {
    if (event.target === modal) {
      modal.style.display = "none";
      clearForms();
    }
  }
};

// --- Search Products ---
async function searchProducts(query, resultsId) {
  // 1. IMPROVEMENT: Check minimum query length
  if (query.length < 2) {
    document.getElementById(resultsId).innerHTML = "";
    return;
  }

  // 2. BUG FIX: Debounce the search input to limit API calls (optional but highly recommended)
  // You would typically use a library or implement a simple debounce function here.
  // For this fix, we focus on the core logic.

  try {
    const response = await fetch(
      `/api/search_products?q=${encodeURIComponent(query)}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const products = await response.json();

    const resultsContainer = document.getElementById(resultsId);
    resultsContainer.innerHTML = "";

    if (products.length === 0) {
      const noResult = document.createElement("div");
      noResult.className = "search-result-item";
      noResult.textContent = "No products found";
      resultsContainer.appendChild(noResult);
      return;
    }

    products.forEach((product) => {
      const div = document.createElement("div");
      div.className = "search-result-item";

      // 3. BUG FIX: Use the property names returned by your /api/search_products Flask route
      // The Flask route returns 'p_name' and 'p_amount'.
      const productName = product.p_name;
      const productAmount = product.p_amount;

      // 4. IMPROVEMENT: Highlight the search term in the result for better UX
      const highlightedName = productName.replace(
        new RegExp(query, "gi"),
        (match) => `<strong>${match}</strong>`
      );

      // Set the HTML content with available quantity
      div.innerHTML = `${highlightedName} (${productAmount} available)`;

      // Set the search input field value to the full, non-highlighted product name
      div.onclick = () => {
        const searchInputId =
          resultsId === "sellResults"
            ? "sellProductSearch"
            : "clinicProductSearch";
        document.getElementById(searchInputId).value = productName;
        resultsContainer.innerHTML = "";
      };
      resultsContainer.appendChild(div);
    });
  } catch (error) {
    console.error("Error searching products:", error);
    const resultsContainer = document.getElementById(resultsId);
    resultsContainer.innerHTML =
      '<div class="search-result-item error-item">Error searching products</div>';
  }
}

// --- Form Submissions ---

// Add Product
document
  .getElementById("addProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
      name: formData.get("productName").trim(), // Trim whitespace
      quantity: parseInt(formData.get("productQuantity")),
    };

    // Basic input validation
    if (!data.name || data.quantity <= 0 || isNaN(data.quantity)) {
      alert("Please enter a valid name and a quantity greater than 0.");
      return;
    }

    try {
      const response = await fetch("/api/add_product", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product added successfully!");
        closeModal("addProductModal");
        window.location.reload();
      } else {
        alert("Error: " + (result.error || "Unknown server error"));
      }
    } catch (error) {
      alert("Network error adding product. Check console for details.");
      console.error("Error:", error);
    }
  });

// Sell Product
document
  .getElementById("sellProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const productName = document
      .getElementById("sellProductSearch")
      .value.trim();
    const quantity = parseInt(document.getElementById("sellQuantity").value);

    if (!productName) {
      alert("Please select a product from the search results.");
      return;
    }

    if (!quantity || quantity <= 0 || isNaN(quantity)) {
      alert("Please enter a valid quantity (greater than 0).");
      return;
    }

    const data = {
      name: productName,
      quantity: quantity,
    };

    try {
      const response = await fetch("/api/sell_product", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product sold successfully!");
        closeModal("sellProductModal");
        window.location.reload();
      } else {
        alert("Error: " + (result.error || "Unknown server error"));
      }
    } catch (error) {
      alert("Network error selling product. Check console for details.");
      console.error("Error:", error);
    }
  });

// Send to Clinic
document
  .getElementById("clinicProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const productName = document
      .getElementById("clinicProductSearch")
      .value.trim();

    if (!productName) {
      alert("Please select a product from the search results.");
      return;
    }

    const data = {
      name: productName,
    };

    try {
      const response = await fetch("/api/send_to_clinic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product sent to clinic successfully!");
        closeModal("clinicProductModal");
        window.location.reload();
      } else {
        alert("Error: " + (result.error || "Unknown server error"));
      }
    } catch (error) {
      alert(
        "Network error sending product to clinic. Check console for details."
      );
      console.error("Error:", error);
    }
  });

// --- Keep Alive Logic ---

// 5. CLEANUP: Move keep-alive setup inside DOMContentLoaded for better practice
document.addEventListener("DOMContentLoaded", function () {
  // Keep-alive to prevent dyno sleep on platforms like Render/Heroku (runs every 4 minutes)
  const keepAlive = () => {
    fetch("/keep-alive").catch((err) =>
      console.error("Keep-alive failed:", err)
    );
  };

  // Run immediately, then every 4 minutes (240000ms)
  keepAlive();
  setInterval(keepAlive, 240000);

  // Note: You must define a lightweight '/keep-alive' endpoint in your Flask app.
});
// Initialize when page loads
document.addEventListener("DOMContentLoaded", function () {
  // Any initialization code if needed
});

setInterval(() => {
  fetch("/keep-alive"); // hit a lightweight endpoint on your server
}, 240000);
