import { Routes, Route } from "react-router-dom";
import data from "./data/products.json";
import Header from "./components/Header";
import ProductGrid from "./components/ProductGrid";
import ProductPage from "./components/ProductPage";

export default function App() {
  const products = data.products;

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
