"use client";

import styles from "@/app/admin/theory-bets/eda/page.module.css";
import { SUPPORTED_LEAGUES, type LeagueCode } from "@/lib/constants/sports";
import type { AvailableStatKeysResponse, TargetDefinition, CleaningOptions } from "@/lib/api/sportsAdmin";
import { TargetDefinitionCard } from "./TargetDefinitionCard";
import { TriggerLogicCard } from "./TriggerLogicCard";
import { ExposureControlsCard } from "./ExposureControlsCard";
import type { TriggerDefinition, ExposureControls, GeneratedFeature } from "@/lib/api/sportsAdmin";

export interface TheoryFormState {
  leagueCode: LeagueCode;
  seasons: string;
  seasonScope: "full" | "current" | "recent";
  recentDays: string;
  phase: "all" | "out_conf" | "conf" | "postseason";
  team: string;
  player: string;
  homeSpreadMin: string;
  homeSpreadMax: string;
  seasonType: string;
  marketType: string;
  side: string;
  closingOnly: boolean;
  includePlayerStats: boolean;
  teamStatKeys: string[];
  playerStatKeys: string[];
}

interface TheoryFormProps {
  form: TheoryFormState;
  setForm: React.Dispatch<React.SetStateAction<TheoryFormState>>;
  pipelineStep: string;
  statKeys: AvailableStatKeysResponse | null;
  loadingStatKeys: boolean;
  toggleStatKey: (type: "teamStatKeys" | "playerStatKeys", key: string) => void;
  selectAllStatKeys: (type: "teamStatKeys" | "playerStatKeys") => void;
  clearStatKeys: (type: "teamStatKeys" | "playerStatKeys") => void;
  handleLeagueChange: (code: LeagueCode) => void;
  // Target/Trigger/Exposure
  targetDefinition: TargetDefinition;
  setTargetDefinition: React.Dispatch<React.SetStateAction<TargetDefinition>>;
  targetLocked: boolean;
  setTargetLocked: React.Dispatch<React.SetStateAction<boolean>>;
  triggerDefinition: TriggerDefinition;
  setTriggerDefinition: React.Dispatch<React.SetStateAction<TriggerDefinition>>;
  exposureControls: ExposureControls;
  setExposureControls: React.Dispatch<React.SetStateAction<ExposureControls>>;
  diagnosticMode: boolean;
  setDiagnosticMode: React.Dispatch<React.SetStateAction<boolean>>;
  includeRestDays: boolean;
  setIncludeRestDays: React.Dispatch<React.SetStateAction<boolean>>;
  includeRolling: boolean;
  setIncludeRolling: React.Dispatch<React.SetStateAction<boolean>>;
  rollingWindow: number;
  setRollingWindow: React.Dispatch<React.SetStateAction<number>>;
  generatedFeatures: GeneratedFeature[];
  featureSummary: string | null;
  featureError: string | null;
  onGenerateFeatures: () => void;
  onRunAnalysis: () => void;
  onBuildModel: () => void;
  analysisRunning: boolean;
  modelRunning: boolean;
  isStatTarget: boolean;
  mcAvailable: boolean;
  mcReason: string | null;
  canAddFeatures: boolean;
  selectedFeatureCount: number;
}

export function TheoryForm({
  form,
  setForm,
  pipelineStep,
  statKeys,
  loadingStatKeys,
  toggleStatKey,
  selectAllStatKeys,
  clearStatKeys,
  handleLeagueChange,
  targetDefinition,
  setTargetDefinition,
  targetLocked,
  setTargetLocked,
  triggerDefinition,
  setTriggerDefinition,
  exposureControls,
  setExposureControls,
  diagnosticMode,
  setDiagnosticMode,
  includeRestDays,
  setIncludeRestDays,
  includeRolling,
  setIncludeRolling,
  rollingWindow,
  setRollingWindow,
  generatedFeatures,
  featureSummary,
  featureError,
  onGenerateFeatures,
  onRunAnalysis,
  onBuildModel,
  analysisRunning,
  modelRunning,
  isStatTarget,
  mcAvailable,
  mcReason,
  canAddFeatures,
  selectedFeatureCount,
}: TheoryFormProps) {
  const hidden = pipelineStep !== "theory";

  return (
    <>
      {/* League */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>League</label>
        <select
          className={styles.select}
          value={form.leagueCode}
          onChange={(e) => handleLeagueChange(e.target.value as LeagueCode)}
        >
          {SUPPORTED_LEAGUES.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </div>

      {/* Seasons */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Seasons (comma separated)</label>
        <input
          className={styles.input}
          type="text"
          value={form.seasons}
          onChange={(e) => setForm((prev) => ({ ...prev, seasons: e.target.value }))}
          placeholder="2023, 2024"
        />
      </div>

      {/* Season scope */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Season scope</label>
        <select
          className={styles.select}
          value={form.seasonScope}
          onChange={(e) => setForm((prev) => ({ ...prev, seasonScope: e.target.value as "full" | "current" | "recent" }))}
        >
          <option value="full">Full season (all selected seasons)</option>
          <option value="current">Current season (latest selected)</option>
          <option value="recent">Recent window (days)</option>
        </select>
      </div>

      {/* Recent days */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Recent days</label>
        <input
          className={styles.input}
          type="number"
          min={1}
          max={365}
          value={form.recentDays}
          onChange={(e) => setForm((prev) => ({ ...prev, recentDays: e.target.value }))}
          disabled={form.seasonScope !== "recent"}
        />
        <p className={styles.hint}>Used only when scope = Recent.</p>
      </div>

      {/* Phase */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Phase (NCAAB)</label>
        <select
          className={styles.select}
          value={form.phase}
          onChange={(e) => setForm((prev) => ({ ...prev, phase: e.target.value as TheoryFormState["phase"] }))}
        >
          <option value="all">All</option>
          <option value="out_conf">Out of conference (before 01/01)</option>
          <option value="conf">Conference (01/01 – 03/15)</option>
          <option value="postseason">Postseason (03/16+)</option>
        </select>
        <p className={styles.hint}>Applied only for NCAAB; ignored for other leagues.</p>
      </div>

      {/* Team filter */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Team filter (optional)</label>
        <input
          className={styles.input}
          type="text"
          placeholder="Team name / short name / abbreviation"
          value={form.team}
          onChange={(e) => setForm((prev) => ({ ...prev, team: e.target.value }))}
        />
      </div>

      {/* Player filter */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Player filter (optional)</label>
        <input
          className={styles.input}
          type="text"
          placeholder="Player name substring"
          value={form.player}
          onChange={(e) => setForm((prev) => ({ ...prev, player: e.target.value }))}
        />
      </div>

      {/* Season type */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Season type (optional)</label>
        <input
          className={styles.input}
          type="text"
          placeholder="regular, playoffs, tournament..."
          value={form.seasonType}
          onChange={(e) => setForm((prev) => ({ ...prev, seasonType: e.target.value }))}
        />
      </div>

      {/* Market type */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Market type (optional)</label>
        <select
          className={styles.select}
          value={form.marketType}
          onChange={(e) => setForm((prev) => ({ ...prev, marketType: e.target.value }))}
        >
          <option value="">Any</option>
          <option value="spread">Spread</option>
          <option value="total">Total</option>
          <option value="moneyline">Moneyline</option>
        </select>
      </div>

      {/* Side */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Side (optional)</label>
        <select
          className={styles.select}
          value={form.side}
          onChange={(e) => setForm((prev) => ({ ...prev, side: e.target.value }))}
        >
          <option value="">Any</option>
          <option value="home">Home</option>
          <option value="away">Away</option>
          <option value="over">Over</option>
          <option value="under">Under</option>
        </select>
      </div>

      {/* Spread min/max */}
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Home spread min</label>
        <input
          className={styles.input}
          type="number"
          value={form.homeSpreadMin}
          onChange={(e) => setForm((prev) => ({ ...prev, homeSpreadMin: e.target.value }))}
          placeholder="0"
        />
      </div>
      <div className={styles.field} hidden={hidden}>
        <label className={styles.label}>Home spread max</label>
        <input
          className={styles.input}
          type="number"
          value={form.homeSpreadMax}
          onChange={(e) => setForm((prev) => ({ ...prev, homeSpreadMax: e.target.value }))}
          placeholder="9.5"
        />
      </div>

      {/* Team stat keys */}
      <div className={styles.fieldFull} hidden={hidden}>
        <label className={styles.label}>
          Stats to include in results (team)
          {loadingStatKeys && <span className={styles.loadingBadge}>Loading...</span>}
          {!loadingStatKeys && statKeys && (
            <span className={styles.countBadge}>
              {form.teamStatKeys.length}/{statKeys.team_stat_keys.length} selected
            </span>
          )}
        </label>
        {statKeys && statKeys.team_stat_keys.length > 0 ? (
          <>
            <div className={styles.statKeyActions}>
              <button type="button" className={styles.linkButton} onClick={() => selectAllStatKeys("teamStatKeys")}>
                Select all
              </button>
              <button type="button" className={styles.linkButton} onClick={() => clearStatKeys("teamStatKeys")}>
                Clear
              </button>
            </div>
            <div className={styles.checkboxGrid}>
              {statKeys.team_stat_keys.map((key) => (
                <label key={key} className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={form.teamStatKeys.includes(key)}
                    onChange={() => toggleStatKey("teamStatKeys", key)}
                  />
                  <span className={styles.checkboxText}>{key}</span>
                </label>
              ))}
            </div>
          </>
        ) : (
          <p className={styles.hint}>
            {loadingStatKeys ? "Loading available stats..." : "No team stats found for this league."}
          </p>
        )}
        <p className={styles.hint}>
          These control what shows up in results/exports. They do not auto-trigger feature engineering.
        </p>
      </div>

      {/* Player stat keys */}
      <div className={styles.fieldFull} hidden={hidden}>
        <label className={styles.label}>
          Stats to include in results (player)
          {loadingStatKeys && <span className={styles.loadingBadge}>Loading...</span>}
          {!loadingStatKeys && statKeys && (
            <span className={styles.countBadge}>
              {form.playerStatKeys.length}/{statKeys.player_stat_keys.length} selected
            </span>
          )}
        </label>
        {statKeys && statKeys.player_stat_keys.length > 0 ? (
          <>
            <div className={styles.statKeyActions}>
              <button type="button" className={styles.linkButton} onClick={() => selectAllStatKeys("playerStatKeys")}>
                Select all
              </button>
              <button type="button" className={styles.linkButton} onClick={() => clearStatKeys("playerStatKeys")}>
                Clear
              </button>
            </div>
            <div className={styles.checkboxGrid}>
              {statKeys.player_stat_keys.map((key) => (
                <label key={key} className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={form.playerStatKeys.includes(key)}
                    onChange={() => toggleStatKey("playerStatKeys", key)}
                  />
                  <span className={styles.checkboxText}>{key}</span>
                </label>
              ))}
            </div>
          </>
        ) : (
          <p className={styles.hint}>
            {loadingStatKeys ? "Loading available stats..." : "No player stats found for this league."}
          </p>
        )}
        <p className={styles.hint}>
          Use these to control what you want to display or explore later; they will not derive features during Analyze.
        </p>
      </div>

      {/* Context / diagnostic toggles */}
      <div className={styles.fieldFull} hidden={hidden}>
        <div className={styles.toggleRow}>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={includeRestDays}
              onChange={(e) => setIncludeRestDays(e.target.checked)}
            />
            Include rest-days feature
          </label>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={includeRolling}
              onChange={(e) => setIncludeRolling(e.target.checked)}
            />
            Include rolling features
          </label>
          <label className={styles.inlineField}>
            Rolling window
            <input
              className={styles.inputInline}
              type="number"
              min={2}
              max={20}
              value={rollingWindow}
              onChange={(e) => setRollingWindow(Number(e.target.value) || 5)}
              disabled={!includeRolling}
            />
          </label>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={diagnosticMode}
              onChange={(e) => setDiagnosticMode(e.target.checked)}
            />
            Diagnostic (post-game features)
          </label>
        </div>
      </div>

      {/* Cards */}
      <div className={styles.fieldFull} hidden={hidden}>
        <TargetDefinitionCard
          targetDefinition={targetDefinition}
          onChange={setTargetDefinition}
          targetLocked={targetLocked}
          onToggleLock={() => setTargetLocked((prev) => !prev)}
        />
      </div>
      <div className={styles.fieldFull} hidden={hidden}>
        <TriggerLogicCard triggerDefinition={triggerDefinition} onChange={setTriggerDefinition} />
      </div>
      <div className={styles.fieldFull} hidden={hidden}>
        <ExposureControlsCard exposureControls={exposureControls} onChange={setExposureControls} targetDefinition={targetDefinition} />
      </div>

      {/* Action buttons */}
      <div className={styles.fieldFull} hidden={hidden}>
        <div className={styles.previewActions}>
          <button
            type="button"
            className={styles.primaryButton}
            disabled={analysisRunning}
            onClick={onRunAnalysis}
          >
            {analysisRunning ? "Analyzing…" : "Analyze theory"}
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={!canAddFeatures || analysisRunning}
            onClick={onGenerateFeatures}
          >
            Add explanatory features
          </button>
          <button
            type="button"
            className={styles.primaryButton}
            disabled={selectedFeatureCount === 0 || modelRunning || analysisRunning}
            onClick={onBuildModel}
          >
            {modelRunning ? "Building…" : "Build model"}
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={
              selectedFeatureCount === 0 || modelRunning || analysisRunning || (isStatTarget && !mcAvailable)
            }
            onClick={onBuildModel}
            title={isStatTarget ? "Not eligible: stat targets have no market distribution" : mcReason ?? undefined}
          >
            Run MC
          </button>
        </div>
        {featureError && <div className={styles.error}>{featureError}</div>}
        {featureSummary && <p className={styles.hint}>{featureSummary}</p>}
      </div>
    </>
  );
}

