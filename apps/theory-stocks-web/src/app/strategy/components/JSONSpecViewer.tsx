import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils/cn";

interface JSONSpecViewerProps {
  title: string;
  data: unknown;
  className?: string;
}

export function JSONSpecViewer({ title, data, className }: JSONSpecViewerProps) {
  return (
    <Card className={cn("bg-card/70", className)}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[380px] overflow-auto rounded-lg bg-muted/60 p-4 text-xs leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}

