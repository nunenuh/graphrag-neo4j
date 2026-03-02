import { useState } from 'react'
import { queryGraph } from '@/lib/api'
import type { QueryResponse } from '@/lib/types'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

const EXAMPLES = [
  'What methods are used for object detection?',
  'Which papers introduced transformer models for NLP?',
  'What datasets benchmark image segmentation?',
  'Find variants of BERT and the tasks they solve.',
]

const LABEL_COLORS: Record<string, string> = {
  Paper: 'bg-blue-100 text-blue-700',
  Method: 'bg-green-100 text-green-700',
  Task: 'bg-amber-100 text-amber-700',
  Dataset: 'bg-purple-100 text-purple-700',
}

interface Props {
  onResult: (r: QueryResponse) => void
  isLoading: boolean
  setIsLoading: (v: boolean) => void
}

export default function ChatPanel({ onResult, isLoading, setIsLoading }: Props) {
  const [q, setQ]             = useState('')
  const [answer, setAnswer]   = useState('')
  const [latency, setLatency] = useState<number | null>(null)
  const [seeds, setSeeds]     = useState<QueryResponse['seed_nodes']>([])
  const [error, setError]     = useState('')

  async function submit(question: string) {
    if (!question.trim() || isLoading) return
    setIsLoading(true); setError('')
    try {
      const res = await queryGraph(question)
      setAnswer(res.answer)
      setLatency(res.latency_ms)
      setSeeds(res.seed_nodes)
      onResult(res)
    } catch {
      setError('Backend unreachable. Is the server running?')
    } finally { setIsLoading(false) }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <h2 className="font-semibold text-gray-800">Ask the Knowledge Graph</h2>

      {/* Example questions */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map(e => (
          <button key={e} onClick={() => { setQ(e); submit(e) }}
            className="text-xs px-2 py-1 bg-slate-100 text-slate-700 rounded-full hover:bg-slate-200 transition-colors">
            {e}
          </button>
        ))}
      </div>

      {/* Input row */}
      <div className="flex gap-2">
        <Input
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit(q)}
          placeholder="Ask about ML papers, methods, datasets..."
        />
        <Button onClick={() => submit(q)} disabled={isLoading}>
          {isLoading ? '...' : 'Ask'}
        </Button>
      </div>

      {/* Seed node badges */}
      {seeds.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-gray-400">Matched:</span>
          {seeds.map(s => (
            <Badge key={s.id} className={LABEL_COLORS[s.label] ?? ''} variant="outline">
              {s.label}: {s.name} ({s.score.toFixed(2)})
            </Badge>
          ))}
        </div>
      )}

      {/* Answer */}
      {answer && (
        <ScrollArea className="flex-1 bg-slate-50 rounded-lg p-4 text-sm">
          <div className="text-xs text-gray-400 mb-1">
            Answer {latency != null && `· ${latency}ms`}
          </div>
          <p className="whitespace-pre-wrap text-gray-700">{answer}</p>
        </ScrollArea>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{error}</div>
      )}
    </div>
  )
}
