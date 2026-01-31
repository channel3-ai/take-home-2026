export interface Price {
  price: number;
  currency: string;
  compare_at_price?: number | null;
}

export interface Variant {
  variant_type: string;
  variant_value: string;
  sku?: string | null;
  price?: Price | null;
  in_stock?: boolean | null;
  image_urls?: string[] | null;
}

export interface Product {
  name: string;
  brand: string;
  price: Price;
  image_urls: string[];
  colors?: string[];
  description?: string;
  key_features?: string[];
  variants?: Variant[];
}
