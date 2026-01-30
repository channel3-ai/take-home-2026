import { useState, useEffect } from 'react'
import { useLocation, Link, useNavigate } from 'react-router-dom'
import { formatPrice, formatComparePrice } from '@/lib/api'
import type { Product } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from '@/components/ui/carousel'

interface LocationState {
  product?: Product
}

export default function ProductDetail() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state as LocationState | null
  const product = state?.product
  
  const [selectedColor, setSelectedColor] = useState<string | null>(null)

  // Set initial selected color when product loads
  useEffect(() => {
    if (product && product.colors.length > 0) {
      setSelectedColor(product.colors[0])
    }
  }, [product])

  // If no product in state (e.g., direct URL access), redirect to home
  if (!product) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">Product not found</p>
        <p className="text-sm text-gray-400 mb-6">
          Please select a product from the catalog
        </p>
        <Button variant="outline" onClick={() => navigate('/')}>
          Browse Products
        </Button>
      </div>
    )
  }

  const comparePrice = formatComparePrice(product.price)
  const isOnSale = comparePrice !== null

  return (
    <div>
      {/* Back button */}
      <Link
        to="/"
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-900 mb-6"
      >
        <svg
          className="w-4 h-4 mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to products
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
        {/* Image Carousel */}
        <div className="relative">
          {product.image_urls.length > 1 ? (
            <Carousel className="w-full">
              <CarouselContent>
                {product.image_urls.map((url, index) => (
                  <CarouselItem key={index}>
                    <div className="aspect-square bg-gray-50 rounded-lg overflow-hidden">
                      <img
                        src={url}
                        alt={`${product.name} - Image ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </CarouselItem>
                ))}
              </CarouselContent>
              <CarouselPrevious className="left-2" />
              <CarouselNext className="right-2" />
            </Carousel>
          ) : (
            <div className="aspect-square bg-gray-50 rounded-lg overflow-hidden">
              <img
                src={product.image_urls[0] || '/placeholder.svg'}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            </div>
          )}
        </div>

        {/* Product Info */}
        <div className="flex flex-col">
          {/* Brand & Category */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-gray-500 uppercase tracking-wide">
              {product.brand}
            </span>
            <span className="text-gray-300">|</span>
            <Badge variant="outline" className="text-xs font-normal">
              {product.category.name}
            </Badge>
          </div>

          {/* Name */}
          <h1 className="text-2xl md:text-3xl font-semibold text-gray-900 mb-4">
            {product.name}
          </h1>

          {/* Price */}
          <div className="flex items-center gap-3 mb-6">
            <span className={`text-2xl font-bold ${isOnSale ? 'text-red-600' : 'text-gray-900'}`}>
              {formatPrice(product.price)}
            </span>
            {isOnSale && (
              <>
                <span className="text-lg text-gray-400 line-through">
                  {comparePrice}
                </span>
                <Badge variant="destructive">Sale</Badge>
              </>
            )}
          </div>

          {/* Description */}
          <p className="text-gray-600 leading-relaxed mb-6">
            {product.description}
          </p>

          {/* Colors */}
          {product.colors.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                Color: <span className="font-normal text-gray-600">{selectedColor}</span>
              </h3>
              <div className="flex flex-wrap gap-2">
                {product.colors.map((color) => (
                  <button
                    key={color}
                    onClick={() => setSelectedColor(color)}
                    className={`px-4 py-2 text-sm rounded-md border transition-colors ${
                      selectedColor === color
                        ? 'border-gray-900 bg-gray-900 text-white'
                        : 'border-gray-200 hover:border-gray-400 text-gray-700'
                    }`}
                  >
                    {color}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Variants */}
          {product.variants.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Variants</h3>
              <div className="flex flex-wrap gap-2">
                {product.variants.map((variant, index) => (
                  <Badge key={index} variant="secondary" className="text-sm py-1 px-3">
                    {typeof variant === 'object' ? JSON.stringify(variant) : String(variant)}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Add to Cart Button */}
          <Button size="lg" className="w-full md:w-auto mt-auto">
            Add to Cart
          </Button>

          {/* Key Features */}
          {product.key_features.length > 0 && (
            <div className="mt-8 pt-8 border-t">
              <h3 className="text-sm font-medium text-gray-900 mb-4">Key Features</h3>
              <ul className="space-y-2">
                {product.key_features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2 text-gray-600">
                    <svg
                      className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
