/// Modal functions
function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
  // Clear previous results when opening modals
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

// Search products
async function searchProducts(query, resultsId) {
  if (query.length < 2) {
    document.getElementById(resultsId).innerHTML = "";
    return;
  }

  try {
    const response = await fetch(
      `/api/search_products?q=${encodeURIComponent(query)}`
    );
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
      div.textContent = `${product.name} (${product.quantity} available)`;
      div.onclick = () => {
        const searchInputId =
          resultsId === "sellResults"
            ? "sellProductSearch"
            : "clinicProductSearch";
        document.getElementById(searchInputId).value = product.name;
        resultsContainer.innerHTML = "";
      };
      resultsContainer.appendChild(div);
    });
  } catch (error) {
    console.error("Error searching products:", error);
  }
}

// Form submissions
document
  .getElementById("addProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
      name: formData.get("productName"),
      quantity: parseInt(formData.get("productQuantity")),
    };

    try {
      const response = await fetch("/api/add_product", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product added successfully!");
        closeModal("addProductModal");
        // Reload the page to update the product list
        window.location.reload();
      } else {
        alert("Error: " + result.error);
      }
    } catch (error) {
      alert("Error adding product");
      console.error("Error:", error);
    }
  });

document
  .getElementById("sellProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const productName = document
      .getElementById("sellProductSearch")
      .value.trim();
    const quantity = parseInt(document.getElementById("sellQuantity").value);

    if (!productName) {
      alert("Please select a product from the search results");
      return;
    }

    if (!quantity || quantity <= 0) {
      alert("Please enter a valid quantity");
      return;
    }

    const data = {
      name: productName,
      quantity: quantity,
    };

    try {
      const response = await fetch("/api/sell_product", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product sold successfully!");
        closeModal("sellProductModal");
        // Reload the page to update the product list
        window.location.reload();
      } else {
        alert("Error: " + result.error);
      }
    } catch (error) {
      alert("Error selling product");
      console.error("Error:", error);
    }
  });

document
  .getElementById("clinicProductForm")
  ?.addEventListener("submit", async function (e) {
    e.preventDefault();

    const productName = document
      .getElementById("clinicProductSearch")
      .value.trim();

    if (!productName) {
      alert("Please select a product from the search results");
      return;
    }

    const data = {
      name: productName,
    };

    try {
      const response = await fetch("/api/send_to_clinic", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.success) {
        alert("Product sent to clinic successfully!");
        closeModal("clinicProductModal");
        // Reload the page to update the product list
        window.location.reload();
      } else {
        alert("Error: " + result.error);
      }
    } catch (error) {
      alert("Error sending product to clinic");
      console.error("Error:", error);
    }
  });

// Initialize when page loads
document.addEventListener("DOMContentLoaded", function () {
  // Any initialization code if needed
});
// Initialize when page loads
document.addEventListener("DOMContentLoaded", function () {
  // Any initialization code if needed
});

setInterval(() => {
  fetch("/keep-alive"); // hit a lightweight endpoint on your server
}, 240000);
