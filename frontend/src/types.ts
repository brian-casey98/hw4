export type Account = {
  id: number
  name: string
  first_name: string
  last_name: string
  email: string
}

export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
}

export type InventoryRow = {
  size: string
  quantity: number
}

export type ProductDetail = Product & {
  inventory: InventoryRow[]
}
