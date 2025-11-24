"use client";

import type { PlaybookText, CatalystAnalysis, AssetBreakdownItem } from "@dock108/js-core";
import { Card } from "@/components/ui/card";

interface PlaybookTabProps {
  playbook: PlaybookText;
  catalystAnalysis?: CatalystAnalysis;
  assetBreakdown?: AssetBreakdownItem[];
}

export function PlaybookTab({ playbook, catalystAnalysis, assetBreakdown }: PlaybookTabProps) {
  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-semibold mb-4">{playbook.title}</h2>
        <p className="text-base leading-relaxed text-foreground mb-6">{playbook.summary}</p>

        {playbook.narrativeSummary && (
          <div className="mb-6 p-4 bg-muted rounded-lg">
            <h3 className="text-lg font-semibold mb-2">Narrative Summary</h3>
            <p className="text-sm leading-relaxed text-foreground">{playbook.narrativeSummary}</p>
          </div>
        )}

        {playbook.deepDive && playbook.deepDive.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Deep Dive</h3>
            <ul className="space-y-2 list-disc list-inside">
              {playbook.deepDive.map((item, idx) => (
                <li key={idx} className="text-sm text-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {catalystAnalysis && (
          <div className="mb-6 p-4 border border-border rounded-lg">
            <h3 className="text-lg font-semibold mb-3">Catalyst Analysis</h3>
            <div className="space-y-3 text-sm">
              <div>
                <span className="font-medium">Type:</span> {catalystAnalysis.type}
              </div>
              <div>
                <span className="font-medium">Description:</span> {catalystAnalysis.description}
              </div>
              {catalystAnalysis.affectedCategories.length > 0 && (
                <div>
                  <span className="font-medium">Affected Categories:</span> {catalystAnalysis.affectedCategories.join(", ")}
                </div>
              )}
              {catalystAnalysis.probableMarketReactions && (
                <div className="mt-3 space-y-2">
                  <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded">
                    <span className="font-medium">If Positive:</span> {catalystAnalysis.probableMarketReactions.ifCatalystPositive}
                  </div>
                  <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded">
                    <span className="font-medium">If Negative:</span> {catalystAnalysis.probableMarketReactions.ifCatalystNegative}
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-900/20 rounded">
                    <span className="font-medium">If Neutral:</span> {catalystAnalysis.probableMarketReactions.ifCatalystNeutral}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {assetBreakdown && assetBreakdown.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Asset-by-Asset Breakdown</h3>
            <div className="space-y-4">
              {assetBreakdown.map((asset, idx) => (
                <div key={idx} className="p-4 border border-border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-lg">{asset.asset}</h4>
                    <span className={`text-xs px-2 py-1 rounded ${
                      asset.confidence === "High" ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400" :
                      asset.confidence === "Medium" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400" :
                      "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400"
                    }`}>
                      {asset.confidence} Confidence
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">Reasoning:</span> {asset.reasoning}
                    </div>
                    <div>
                      <span className="font-medium">Expected Reaction:</span> {asset.reaction}
                    </div>
                    {asset.entryPlan.length > 0 && (
                      <div>
                        <span className="font-medium">Entry Plan:</span>
                        <ul className="list-disc list-inside ml-2 mt-1">
                          {asset.entryPlan.map((plan, pIdx) => (
                            <li key={pIdx}>{plan}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {asset.risks.length > 0 && (
                      <div>
                        <span className="font-medium">Risks:</span>
                        <ul className="list-disc list-inside ml-2 mt-1">
                          {asset.risks.map((risk, rIdx) => (
                            <li key={rIdx}>{risk}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {playbook.gamePlan.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Game Plan</h3>
            <ul className="space-y-2 list-disc list-inside">
              {playbook.gamePlan.map((item, idx) => (
                <li key={idx} className="text-sm text-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {playbook.guardrails.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Guardrails</h3>
            <ul className="space-y-2 list-disc list-inside">
              {playbook.guardrails.map((item, idx) => (
                <li key={idx} className="text-sm text-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {playbook.dataSources.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-3">Data We're Leaning On</h3>
            <p className="text-sm text-foreground">{playbook.dataSources.join(", ")}</p>
          </div>
        )}
      </Card>
    </div>
  );
}

