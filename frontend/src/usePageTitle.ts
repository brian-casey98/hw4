import { useEffect } from 'react'

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title === 'Campus Customs' ? title : `${title} · Campus Customs`
  }, [title])
}
