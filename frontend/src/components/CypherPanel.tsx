import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'

export default function CypherPanel({ cypher }: { cypher: string }) {
  const [open, setOpen] = useState(false)
  if (!cypher) return null

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="border-t border-gray-200">
      <CollapsibleTrigger className="w-full flex items-center gap-2 px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        Cypher query used
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="px-4 py-3 bg-gray-900 text-green-400 text-xs overflow-x-auto font-mono">
          {cypher}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  )
}
