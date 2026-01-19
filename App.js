import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);

  // Fetch products from backend on load
  useEffect(() => {
    fetch('http://localhost:5000/api/products')
      .then(res => res.json())
      .then(data => setProducts(data))
      .catch(err => console.error("Error fetching data:", err));
  }, []);

  // Add item to cart
  const addToCart = (product) => {
    setCart([...cart, product]);
    alert(`${product.name} added to cart!`);
  };

  return (
    <div className="app-container">
      {/* Header / Navbar */}
      <header className="navbar">
        <div className="logo">AmazonClone</div>
        <div className="search-bar">
          <input type="text" placeholder="Search for products..." />
          <button>Search</button>
        </div>
        <div className="cart-icon">
          Cart ({cart.length})
        </div>
      </header>

      {/* Product Grid */}
      <main className="product-list">
        {products.map((product) => (
          <div key={product.id} className="product-card">
            <img src={product.image} alt={product.name} />
            <h3>{product.name}</h3>
            <div className="rating">⭐ {product.rating}</div>
            <p className="price">${product.price}</p>
            <button 
              className="add-btn" 
              onClick={() => addToCart(product)}
            >
              Add to Cart
            </button>
          </div>
        ))}
      </main>
    </div>
  );
}

export default App;
