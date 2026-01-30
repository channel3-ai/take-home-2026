import type { Product, Price } from './types'

// Use environment variable for API URL - never hardcode sensitive endpoints
const API_BASE_URL = import.meta.env.VITE_API_URL 

export async function fetchProducts(): Promise<Product[]> {
  const response = await fetch(`${API_BASE_URL}/products`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'omit',
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch products')
  }
  
  const data = await response.json()
  return data.products  // ✅ Extract just the products array
}

export function formatPrice(price: Price): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: price.currency || 'USD',
  }).format(price.price)
}

export function formatComparePrice(price: Price): string | null {
  if (!price.compare_at_price) return null
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: price.currency || 'USD',
  }).format(price.compare_at_price)
}
