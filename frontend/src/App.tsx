import { useState } from 'react'
import { Card } from '@/components/ui/card'
import ChatPanel from '@/components/ChatPanel'
import GraphViewer from '@/components/GraphViewer'
import CypherPanel from '@/components/CypherPanel'
import type { QueryResponse } from '@/lib/types'

export default function App() {
  const [result, setResult]       = useState<QueryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center gap-3">
        <span className="text-xl">🧠</span>
        <h1 className="font-semibold text-gray-900">Graph RAG Explorer</h1>
        <span className="text-xs text-gray-400 ml-2">
          ML Knowledge Graph · Neo4j + OpenAI
        </span>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden p-4 gap-4">
        {/* Left: Chat */}
        <Card className="w-2/5 flex flex-col overflow-hidden">
          <ChatPanel
            onResult={setResult}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
          />
        </Card>

        {/* Right: Graph + Cypher */}
        <Card className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                Retrieving from knowledge graph...
              </div>
            ) : (
              <GraphViewer
                nodes={result?.nodes ?? []}
                edges={result?.edges ?? []}
                seedNodes={result?.seed_nodes ?? []}
              />
            )}
          </div>
          <CypherPanel cypher={result?.cypher_used ?? ''} />
        </Card>
      </div>
    </div>
  )
}
