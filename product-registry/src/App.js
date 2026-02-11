import { Routes, Route } from "react-router-dom";
import { useState, useEffect } from "react";
import Header from "./components/Header";
import ProductGrid from "./components/ProductGrid";
import ProductPage from "./components/ProductPage";

export default function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await fetch("http://localhost:8000/products/");
        if (!response.ok) {
          throw new Error("Failed to fetch products from backend");
        }
        const data = await response.json();
        setProducts(data.products || []);
        setError(null);
      } catch (err) {
        console.error("Error fetching products:", err);
        setError(err.message);
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  if (loading) {
    return (
      <>
        <Header />
        <main className="container">
          <p>Loading products...</p>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Header />
        <main className="container">
          <p style={{ color: "red" }}>Error: {error}</p>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="container">
        <Routes>
          <Route path="/" element={<ProductGrid products={products} />} />
          <Route path="/product/:id" element={<ProductPage products={products} />} />
        </Routes>
      </main>
    </>
  );
}
