import { Routes, Route } from 'react-router-dom'
import CatalogPage from './pages/CatalogPage'
import ProductDetailPage from './pages/ProductDetailPage'
import './index.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<CatalogPage />} />
      <Route path="/products/:id" element={<ProductDetailPage />} />
    </Routes>
  )
}

export default App
