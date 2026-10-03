import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Product } from './types.ts'

type ChatCard = {
  product_id: string
  name: string
  garment_type: string
  description: string
  price: number
  image_url: string
  colors?: string[]
}

type CatalogueContextValue = {
  matches: Product[] | null
  query: string
  showMatches: (query: string, products: ChatCard[]) => void
  clearMatches: () => void
}

const CatalogueContext = createContext<CatalogueContextValue | null>(null)

function asProduct(card: ChatCard): Product {
  return {
    product_id: card.product_id,
    name: card.name,
    garment_type: card.garment_type,
    description: card.description,
    colors: card.colors ?? [],
    search_tags: [],
    image_file_path: '',
    image_url: card.image_url,
    price: card.price,
  }
}

export function CatalogueProvider({ children }: { children: ReactNode }) {
  const [matches, setMatches] = useState<Product[] | null>(null)
  const [query, setQuery] = useState('')
  const value = useMemo<CatalogueContextValue>(
    () => ({
      matches,
      query,
      showMatches: (nextQuery, products) => {
        setQuery(nextQuery)
        setMatches(products.map(asProduct))
      },
      clearMatches: () => {
        setMatches(null)
        setQuery('')
      },
    }),
    [matches, query],
  )
  return <CatalogueContext.Provider value={value}>{children}</CatalogueContext.Provider>
}

export function useCatalogue(): CatalogueContextValue {
  const value = useContext(CatalogueContext)
  if (!value) {
    throw new Error('useCatalogue must be used inside CatalogueProvider')
  }
  return value
}
