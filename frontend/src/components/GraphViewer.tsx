import { useRef, useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphNode, GraphEdge, SeedNode } from '@/lib/types'

const COLORS: Record<string, string> = {
  Paper: '#3b82f6', Method: '#10b981', Task: '#f59e0b', Dataset: '#8b5cf6',
}

interface Props { nodes: GraphNode[]; edges: GraphEdge[]; seedNodes: SeedNode[] }

export default function GraphViewer({ nodes, edges, seedNodes }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 700, height: 480 })
  const seedIds = new Set(seedNodes.map(s => s.id))

  useEffect(() => {
    if (!containerRef.current) return
    const { offsetWidth, offsetHeight } = containerRef.current
    setDimensions({ width: offsetWidth, height: offsetHeight })
  }, [nodes])

  if (!nodes.length) return (
    <div className="flex items-center justify-center h-full text-gray-400 text-sm">
      Ask a question to see the knowledge graph
    </div>
  )

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        graphData={{
          nodes: nodes.map(n => ({
            id: n.id,
            name: n.name || n.title || n.id,
            label: n.label ?? 'Node',
            val: seedIds.has(n.id as string) ? 3 : 1,
          })),
          links: edges.map(e => ({ source: e.from_id, target: e.to_id, label: e.type })),
        }}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel="name"
        nodeColor={(n: Record<string, unknown>) => seedIds.has(n.id as string)
          ? '#f97316'
          : COLORS[n.label as string] ?? '#6b7280'}
        nodeRelSize={6}
        linkLabel="label"
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkColor={() => '#d1d5db'}
      />
    </div>
  )
}
