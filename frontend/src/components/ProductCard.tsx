import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Product } from '@/lib/types'
import { formatPrice, formatComparePrice } from '@/lib/api'

interface ProductCardProps {
  product: Product
  index: number
}

export default function ProductCard({ product, index }: ProductCardProps) {
  const comparePrice = formatComparePrice(product.price)
  const isOnSale = comparePrice !== null

  return (
    <Link 
      to={`/product/${index}`}
      state={{ product }}
    >
      <Card className="group overflow-hidden border-0 shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer">
        <div className="aspect-square overflow-hidden bg-gray-50">
          <img
            src={product.image_urls[0] || '/placeholder.svg'}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        </div>
        <CardContent className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            {product.brand}
          </p>
          <h3 className="font-medium text-gray-900 line-clamp-2 mb-2 group-hover:text-gray-700">
            {product.name}
          </h3>
          <div className="flex items-center gap-2">
            <span className={`font-semibold ${isOnSale ? 'text-red-600' : 'text-gray-900'}`}>
              {formatPrice(product.price)}
            </span>
            {isOnSale && (
              <span className="text-sm text-gray-400 line-through">
                {comparePrice}
              </span>
            )}
            {isOnSale && (
              <Badge variant="secondary" className="text-xs">
                Sale
              </Badge>
            )}
          </div>
          {product.colors.length > 1 && (
            <p className="text-xs text-gray-500 mt-2">
              {product.colors.length} colors
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
