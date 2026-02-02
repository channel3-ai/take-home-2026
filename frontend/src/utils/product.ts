import type { Product, Price } from '../types/product';

export const formatPrice = (price: Price | null | undefined): string => {
  if (!price || !price.price) return '—';
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: price.currency || 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  return formatter.format(price.price);
};

export const getProductId = (product: Product, index?: number): string => {
  const id = product.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return id || `product-${index ?? product.name}`;
};
