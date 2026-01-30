import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function ProductCardSkeleton() {
  return (
    <Card className="overflow-hidden border-0 shadow-sm">
      <Skeleton className="aspect-square w-full" />
      <CardContent className="p-4">
        <Skeleton className="h-3 w-16 mb-2" />
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-2/3 mb-3" />
        <Skeleton className="h-5 w-20" />
      </CardContent>
    </Card>
  )
}
