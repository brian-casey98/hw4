import { Link } from 'react-router-dom'
import { formatPrice } from '../api.ts'
import type { Product } from '../types.ts'

type ProductCardProps = {
  product: Product
  titleTag?: 'h2' | 'h3'
}

export function ProductCard({ product, titleTag = 'h2' }: ProductCardProps) {
  const Title = titleTag

  return (
    <Link className="card" to={`/products/${product.product_id}`}>
      <div className="card-media">
        <img src={product.image_url} alt={product.name} loading="lazy" />
      </div>
      <div className="card-body">
        <p className="eyebrow">{product.garment_type}</p>
        <Title className="card-name">{product.name}</Title>
        <p className="price">{formatPrice(product.price)}</p>
        <p className="card-description">{product.description}</p>
      </div>
    </Link>
  )
}
