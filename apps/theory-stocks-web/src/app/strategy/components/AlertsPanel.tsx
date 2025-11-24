import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import dayjs from "@/lib/dayjs";
import type { AlertSpec, AlertEvent } from "@dock108/js-core";

interface AlertsPanelProps {
  alertSpec: AlertSpec;
  alerts?: AlertEvent[];
  alertsEnabled: boolean;
  isToggling: boolean;
  onToggle: (enabled: boolean) => Promise<void> | void;
  onRefresh?: () => Promise<void> | void;
}

export function AlertsPanel({ alertSpec, alerts, alertsEnabled, isToggling, onToggle, onRefresh }: AlertsPanelProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">Alerts</CardTitle>
          <p className="text-sm text-muted-foreground">Live triggers from your alertSpec</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {alertsEnabled ? "Enabled" : "Disabled"}
          <Switch checked={alertsEnabled} disabled={isToggling} onClick={() => onToggle(!alertsEnabled)} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <p className="text-xs uppercase text-muted-foreground">Rules</p>
          {alertSpec.triggers.map((trigger) => (
            <div key={trigger.name} className="rounded-lg border border-border/70 p-3">
              <p className="text-sm font-medium">{trigger.name}</p>
              <p className="text-sm text-muted-foreground">{trigger.condition}</p>
              <div className="mt-2 text-xs text-muted-foreground">
                Channel: {trigger.channel} · Cooldown {trigger.cooldownMinutes}m
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase text-muted-foreground">Triggered events</p>
            {onRefresh && (
              <Button size="sm" variant="ghost" onClick={() => onRefresh()}>
                Refresh
              </Button>
            )}
          </div>
          {alerts && alerts.length > 0 ? (
            <ul className="space-y-3">
              {alerts.map((event) => (
                <li key={event.id} className="rounded-lg border border-border/70 p-3">
                  <p className="text-sm font-medium">{event.reason}</p>
                  <p className="text-xs text-muted-foreground">{dayjs(event.triggeredAt).format("MMM D, HH:mm z")}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No alert events yet.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

