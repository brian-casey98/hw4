import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { formatPrice } from '../api.ts'
import { useAuth } from '../auth.tsx'
import { useCatalogue } from '../catalogue.tsx'
import { loadChatHistory, pageHint, requestAssistantReply, type ChatProduct } from '../chat.ts'

type ChatRole = 'user' | 'assistant'

type ChatLine = {
  id: number
  role: ChatRole
  content: string
  products?: ChatProduct[]
}

const greeting: ChatLine = {
  id: 1,
  role: 'assistant',
  content: 'Ask about a hoodie, a college, or a size. I can check the Campus Customs catalogue.',
}

export function ChatWidget() {
  const navigate = useNavigate()
  const location = useLocation()
  const { showMatches } = useCatalogue()
  const { user, ready } = useAuth()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [messages, setMessages] = useState<ChatLine[]>([greeting])

  useEffect(() => {
    if (!ready) return
    if (!user) {
      setMessages([greeting])
      return
    }
    let cancelled = false
    loadChatHistory()
      .then((saved) => {
        if (cancelled) return
        setMessages(saved.length > 0 ? saved : [greeting])
      })
      .catch(() => {
        if (!cancelled) setMessages([greeting])
      })
    return () => {
      cancelled = true
    }
  }, [ready, user])

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = draft.trim()
    if (!message || pending) return

    const userLine: ChatLine = { id: Date.now(), role: 'user', content: message }
    const pendingId = Date.now() + 1
    setMessages((current) => [
      ...current,
      userLine,
      { id: pendingId, role: 'assistant', content: 'Checking the catalogue…' },
    ])
    setDraft('')
    setPending(true)
    try {
      const reply = await requestAssistantReply(message, pageHint(location.pathname))
      setMessages((current) =>
        current.map((line) =>
          line.id === pendingId
            ? { ...line, content: reply.message, products: reply.products }
            : line,
        ),
      )
      if (reply.products.length > 0) {
        showMatches(message, reply.products)
        const onListing = location.pathname === '/' || location.pathname === '/products'
        if (!onListing) navigate('/products')
      }
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : 'The shop assistant could not be reached.'
      setMessages((current) =>
        current.map((line) => (line.id === pendingId ? { ...line, content: detail } : line)),
      )
    } finally {
      setPending(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-launcher" type="button" onClick={() => setOpen(true)}>
        Ask the shop
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Shop chat">
      <header className="chat-header">
        <div>
          <p className="chat-kicker">Campus Customs</p>
          <h2>Shop chat</h2>
        </div>
        <button className="chat-close" type="button" onClick={() => setOpen(false)}>
          Close
        </button>
      </header>
      <div className="chat-log">
        {messages.map((line) => (
          <div key={line.id} className={`chat-line chat-line-${line.role}`}>
            <p>{line.content}</p>
            {line.products && line.products.length > 0 ? (
              <div className="chat-cards">
                {line.products.map((product) => (
                  <Link key={product.product_id} className="chat-card" to={`/products/${product.product_id}`}>
                    <img src={product.image_url} alt="" />
                    <span>
                      <strong>{product.name}</strong>
                      {formatPrice(product.price)}
                    </span>
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="chat-message">
          Message
        </label>
        <input
          id="chat-message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask about a piece"
          autoComplete="off"
        />
        <button type="submit" disabled={pending || draft.trim() === ''}>
          Send
        </button>
      </form>
    </section>
  )
}
