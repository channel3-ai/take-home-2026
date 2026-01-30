import { Routes, Route } from 'react-router-dom'
import ProductGrid from './components/ProductGrid'
import ProductDetail from './components/ProductDetail'

function App() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-2xl font-semibold text-gray-900">Product Store</h1>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<ProductGrid />} />
          <Route path="/product/:index" element={<ProductDetail />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
