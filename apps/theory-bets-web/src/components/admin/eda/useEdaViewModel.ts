import { useCallback, useMemo } from "react";
import {
  type AnalysisResponse,
  type DataQualitySummary,
  type GeneratedFeature,
  type ModelBuildResponse,
  type AvailableStatKeysResponse,
} from "@/lib/api/sportsAdmin";
import { type LeagueCode } from "@/lib/constants/sports";

export type DqSortKey = "null_pct" | "non_numeric" | "name";
export type DqSortDir = "asc" | "desc";

export interface EdaFormState {
  leagueCode: LeagueCode;
  seasons: string;
  seasonScope: "full" | "current" | "recent";
  recentDays: string;
  phase: "all" | "out_conf" | "conf" | "postseason";
  team: string;
  player: string;
  homeSpreadMin: string;
  homeSpreadMax: string;
}

interface UseEdaViewModelParams {
  form: EdaFormState;
  generatedFeatures: GeneratedFeature[];
  analysisResult: AnalysisResponse | null;
  modelResult: ModelBuildResponse | null;
  dataQuality: DataQualitySummary | null;
  dqSearch: string;
  dqHideZero: boolean;
  dqSortKey: DqSortKey;
  dqSortDir: DqSortDir;
  statKeys?: AvailableStatKeysResponse | null;
}

export function useEdaViewModel({
  form,
  generatedFeatures,
  analysisResult,
  modelResult,
  dataQuality,
  dqSearch,
  dqHideZero,
  dqSortKey,
  dqSortDir,
}: UseEdaViewModelParams) {
  const parseSeasons = useCallback((): number[] | undefined => {
    if (!form.seasons.trim()) return undefined;
    const nums = form.seasons
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => Number(s))
      .filter((n) => !Number.isNaN(n));
    return nums.length ? nums : undefined;
  }, [form.seasons]);

  const seasonsForScope = useMemo(() => {
    const parsed = parseSeasons();
    if (!parsed) return undefined;
    if (form.seasonScope === "current") {
      return [Math.max(...parsed)];
    }
    return parsed;
  }, [form.seasonScope, parseSeasons]);

  const recentDaysValue = useMemo(() => {
    if (form.seasonScope !== "recent") return undefined;
    const n = Number(form.recentDays);
    return Number.isFinite(n) && n > 0 ? n : undefined;
  }, [form.seasonScope, form.recentDays]);

  const gamesLink = useMemo(() => {
    const params = new URLSearchParams();
    params.set("league", form.leagueCode);
    if (form.seasons.trim()) params.set("seasons", form.seasons.trim());
    if (form.team.trim()) params.set("team", form.team.trim());
    if (form.player.trim()) params.set("player", form.player.trim());
    const qs = params.toString();
    return `/admin/theory-bets/games${qs ? `?${qs}` : ""}`;
  }, [form.leagueCode, form.seasons, form.team, form.player]);

  const featureLeakageSummary = useMemo(() => {
    const postGame = generatedFeatures.filter((f) => f.timing === "post_game");
    return {
      postGameCount: postGame.length,
      hasPostGame: postGame.length > 0,
    };
  }, [generatedFeatures]);

  const featurePolicyMessage = useMemo(() => {
    const policy = analysisResult?.feature_policy ?? modelResult?.feature_policy;
    if (!policy) return null;
    if (policy.context === "deployable" && policy.dropped_post_game_count > 0) {
      return `Deployable mode: dropped ${policy.dropped_post_game_count} post-game (leakage) features.`;
    }
    if (policy.context === "diagnostic" && policy.contains_post_game_features) {
      return "Diagnostic mode: post-game (leakage) features are allowed for inspection only.";
    }
    return null;
  }, [analysisResult?.feature_policy, modelResult?.feature_policy]);

  const primarySignalDrivers = useMemo(() => {
    if (!modelResult) return null;
    const weights = modelResult.model_summary.feature_weights ?? {};
    const featureMetaByName = new Map<string, { group: string; timing?: string | null }>();
    for (const f of generatedFeatures) {
      featureMetaByName.set(f.name, { group: f.group ?? "Other", timing: f.timing });
    }

    const byGroup: Record<string, number> = {};
    const byFeature = Object.entries(weights).map(([name, w]) => {
      const meta = featureMetaByName.get(name);
      const group = meta?.group ?? "Other";
      const abs = Math.abs(w);
      byGroup[group] = (byGroup[group] ?? 0) + abs;
      return { name, weight: w, abs, group, timing: meta?.timing ?? null };
    });

    const groupRows = Object.entries(byGroup)
      .map(([group, abs]) => ({ group, abs }))
      .sort((a, b) => b.abs - a.abs);

    const topDrivers = byFeature.sort((a, b) => b.abs - a.abs).slice(0, 7);
    return { groupRows, topDrivers };
  }, [modelResult, generatedFeatures]);

  const dataQualityRows = useMemo(() => {
    if (!dataQuality) return [];
    const entries = Object.entries(dataQuality.feature_stats).map(([name, stats]) => ({
      name,
      ...stats,
    }));
    let rows = entries;
    if (dqSearch.trim()) {
      const needle = dqSearch.toLowerCase();
      rows = rows.filter((r) => r.name.toLowerCase().includes(needle));
    }
    if (dqHideZero) {
      rows = rows.filter((r) => r.nulls > 0 || r.non_numeric > 0);
    }
    rows = [...rows].sort((a, b) => {
      const dir = dqSortDir === "asc" ? 1 : -1;
      if (dqSortKey === "name") return a.name.localeCompare(b.name) * dir;
      if (dqSortKey === "non_numeric") return (a.non_numeric - b.non_numeric) * dir;
      return (a.null_pct - b.null_pct) * dir;
    });
    return rows;
  }, [dataQuality, dqSearch, dqHideZero, dqSortKey, dqSortDir]);

  return {
    parseSeasons,
    seasonsForScope,
    recentDaysValue,
    gamesLink,
    featureLeakageSummary,
    featurePolicyMessage,
    primarySignalDrivers,
    dataQualityRows,
  };
}

