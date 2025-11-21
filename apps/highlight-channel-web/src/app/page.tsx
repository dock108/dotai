"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createClient,
  HighlightsAPI,
  type HighlightPlanResponse,
  APIError,
  NetworkError,
} from "@dock108/js-core";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import styles from "./page.module.css";
import {
  SPORT_OPTIONS,
  PLAY_TYPE_SUGGESTIONS,
  MAX_FILTER_ITEMS,
  DATE_PRESETS,
  DURATION_PRESETS,
} from "@/lib/constants";
import { PRESETS } from "@/lib/presets";
import type { BuilderState, ErrorInfo, DatePreset } from "@/lib/types";
import { buildQueryFromState, extractErrorInfo } from "@/lib/utils";

export default function Home() {
  const router = useRouter();
  const apiClient = createClient();
  const highlightsAPI = new HighlightsAPI(apiClient);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [requestStartTime, setRequestStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // Builder state
  const [builderState, setBuilderState] = useState<BuilderState>({
    sports: [],
    teams: [],
    players: [],
    playTypes: [],
    keywords: [],
    datePreset: "last7days",
    customStartDate: "",
    customEndDate: "",
    durationMinutes: 90,
    comments: "",
  });

  // Input states for adding items
  const [teamInput, setTeamInput] = useState("");
  const [playerInput, setPlayerInput] = useState("");
  const [playTypeInput, setPlayTypeInput] = useState("");
  const [keywordInput, setKeywordInput] = useState("");

  const buildQueryFromState = (state: BuilderState): string => {
    const parts: string[] = [];

    // Sports
    if (state.sports.length > 0) {
      parts.push(state.sports.join(", "));
    }

    // Teams
    if (state.teams.length > 0) {
      parts.push(state.teams.join(", "));
    }

    // Players
    if (state.players.length > 0) {
      parts.push(state.players.join(", "));
    }

    // Play types
    if (state.playTypes.length > 0) {
      parts.push(state.playTypes.join(", "));
    }

    // Keywords
    if (state.keywords.length > 0) {
      parts.push(state.keywords.join(", "));
    }

    // Date range
    if (state.datePreset === "custom" && state.customStartDate && state.customEndDate) {
      parts.push(`from ${state.customStartDate} to ${state.customEndDate}`);
    } else if (state.datePreset === "custom" && state.customStartDate) {
      parts.push(`from ${state.customStartDate}`);
    } else if (state.datePreset === "historical" && state.customStartDate && state.customEndDate) {
      parts.push(`from ${state.customStartDate} to ${state.customEndDate}`);
    } else if (state.datePreset !== "custom" && state.datePreset !== "historical") {
      const presetLabels: Record<DatePreset, string> = {
        last2days: "last 48 hours",
        last7days: "last 7 days",
        last14days: "last 14 days",
        last30days: "last 30 days",
        custom: "",
        historical: "",
      };
      parts.push(presetLabels[state.datePreset]);
    }

    // Duration
    parts.push(`${state.durationMinutes} minutes`);

    // Comments (added as context)
    if (state.comments.trim()) {
      parts.push(`(${state.comments})`);
    }

    return parts.join(" ");
  };

  const handleSubmit = async () => {
    if (builderState.sports.length === 0) {
      setError({ message: "Please select at least one sport" });
      return;
    }

    const queryText = buildQueryFromState(builderState);
    
    setError(null);
    setSuccessMessage(null);
    setLoading(true);
    const startTime = Date.now();
    setRequestStartTime(startTime);
    setElapsedTime(0);
    
    const timeInterval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    
    const controller = new AbortController();
    setAbortController(controller);

    try {
      // Build structured request from builder state
      const request: any = {
        query_text: queryText,
        mode: "sports_highlight",
      };
      
      // Add structured fields if builder state has values
      if (builderState.sports.length > 0) {
        request.sports = builderState.sports;
      }
      if (builderState.teams.length > 0) {
        request.teams = builderState.teams;
      }
      if (builderState.players.length > 0) {
        request.players = builderState.players;
      }
      if (builderState.playTypes.length > 0) {
        request.play_types = builderState.playTypes;
      }
      if (builderState.datePreset) {
        request.date_preset = builderState.datePreset;
      }
      if (builderState.customStartDate) {
        request.custom_start_date = builderState.customStartDate;
      }
      if (builderState.customEndDate) {
        request.custom_end_date = builderState.customEndDate;
      }
      if (builderState.durationMinutes) {
        request.duration_minutes = builderState.durationMinutes;
      }
      if (builderState.comments.trim()) {
        request.comments = builderState.comments;
      }
      
      const data = await highlightsAPI.planPlaylist(request);
      
      if (data.items.length === 0) {
        setError({
          code: "NO_VIDEOS_FOUND",
          message: "We couldn't find highlights that match this exactly.",
          suggestions: [
            "Try expanding the date range",
            "Remove some filters to broaden the search",
            "Check if the sport/team names are spelled correctly",
          ],
        });
        setLoading(false);
        return;
      }
      
      const cacheStatus = data.cache_status === "cached" ? "from cache" : "fresh";
      const videoCount = data.items.length;
      const durationMinutes = Math.round(data.total_duration_seconds / 60);
      setSuccessMessage(
        `Highlight show ready! Found ${videoCount} videos (${durationMinutes} minutes, ${cacheStatus}). Redirecting...`
      );
      
      clearInterval(timeInterval);
      setAbortController(null);
      setRequestStartTime(null);
      
      setTimeout(() => {
        router.push(`/playlist/${data.playlist_id}`);
      }, 1000);
    } catch (err: unknown) {
      clearInterval(timeInterval);
      setAbortController(null);
      setRequestStartTime(null);
      const errorInfo = extractErrorInfo(err);
      setError(errorInfo);
    } finally {
      setLoading(false);
      setRequestStartTime(null);
      setElapsedTime(0);
    }
  };

  const handleCancel = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setLoading(false);
    setRequestStartTime(null);
    setElapsedTime(0);
  };

  const handlePreset = (preset: BuilderPreset) => {
    setBuilderState({
      sports: preset.state.sports || [],
      teams: preset.state.teams || [],
      players: preset.state.players || [],
      playTypes: preset.state.playTypes || [],
      keywords: [],
      datePreset: preset.state.datePreset || "last7days",
      customStartDate: preset.state.customStartDate || "",
      customEndDate: preset.state.customEndDate || "",
      durationMinutes: preset.state.durationMinutes || 90,
      comments: preset.state.comments || "",
    });
  };

  const addItem = (type: "teams" | "players" | "playTypes" | "keywords", value: string) => {
    if (!value.trim()) return;
    const current = builderState[type];
    if (current.length >= MAX_FILTER_ITEMS) {
      setError({ message: `Maximum ${MAX_FILTER_ITEMS} ${type} allowed` });
      return;
    }
    if (current.includes(value.trim())) {
      setError({ message: `${value.trim()} is already added` });
      return;
    }
    setBuilderState({
      ...builderState,
      [type]: [...current, value.trim()],
    });
    // Clear input
    if (type === "teams") setTeamInput("");
    if (type === "players") setPlayerInput("");
    if (type === "playTypes") setPlayTypeInput("");
    if (type === "keywords") setKeywordInput("");
    setError(null);
  };

  const removeItem = (type: "teams" | "players" | "playTypes" | "keywords", index: number) => {
    const current = [...builderState[type]];
    current.splice(index, 1);
    setBuilderState({
      ...builderState,
      [type]: current,
    });
  };

  const toggleSport = (sport: string) => {
    const current = [...builderState.sports];
    const index = current.indexOf(sport);
    if (index >= 0) {
      current.splice(index, 1);
    } else {
      current.push(sport);
    }
    setBuilderState({
      ...builderState,
      sports: current,
    });
  };


  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <header className={styles.hero}>
          <h1 className={styles.title}>Catch Up on Recent Sports Highlights</h1>
          <p className={styles.subtitle}>
            Tell us what you missed. We'll find the best highlights from the last few days and build you a custom show.
          </p>
          <button
            className={styles.helpToggle}
            onClick={() => setShowHelp(!showHelp)}
            type="button"
          >
            {showHelp ? "Hide" : "Show"} Tips
          </button>
        </header>
        
        {showHelp && (
          <div className={styles.helpSection}>
            <div className={styles.helpContent}>
              <h3 className={styles.helpTitle}>How It Works</h3>
              <p className={styles.helpText}>
                Select the sports you care about, add specific teams or players, choose a time window, and we'll build a highlight show 
                from the best clips uploaded in the last 48 hours. Perfect for catching up on what you missed.
              </p>
              <div className={styles.disclaimer}>
                <strong>Note:</strong> This app builds playlists using public YouTube videos. We do not host or control the content.
              </div>
            </div>
          </div>
        )}

        <div className={styles.mainSection}>
          {/* Quick Presets */}
          <div className={styles.presetsSection}>
            <p className={styles.presetsLabel}>Quick presets:</p>
            <div className={styles.presets}>
              {PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  className={styles.presetChip}
                  onClick={() => handlePreset(preset)}
                  disabled={loading}
                  type="button"
                >
                  {preset.text}
                </button>
              ))}
            </div>
          </div>

          {/* Builder Form */}
          <div className={styles.builderSection}>
            <h3 className={styles.builderTitle}>Build Your Highlight Show</h3>
            
            {/* Sports Selection */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>Sports (select one or more)</label>
              <div className={styles.sportChips}>
                {SPORT_OPTIONS.map((sport) => (
                  <button
                    key={sport}
                    type="button"
                    className={`${styles.sportChip} ${builderState.sports.includes(sport) ? styles.sportChipActive : ""}`}
                    onClick={() => toggleSport(sport)}
                  >
                    {sport}
                  </button>
                ))}
              </div>
            </div>

            {/* Teams */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>
                Teams (up to {MAX_FILTER_ITEMS})
              </label>
              <div className={styles.chipInputGroup}>
                <input
                  type="text"
                  className={styles.chipInput}
                  value={teamInput}
                  onChange={(e) => setTeamInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("teams", teamInput);
                    }
                  }}
                  placeholder="e.g., Kansas City Chiefs"
                  disabled={loading || builderState.teams.length >= MAX_FILTER_ITEMS}
                />
                <button
                  type="button"
                  className={styles.addButton}
                  onClick={() => addItem("teams", teamInput)}
                  disabled={loading || builderState.teams.length >= MAX_FILTER_ITEMS}
                >
                  Add
                </button>
              </div>
              {builderState.teams.length > 0 && (
                <div className={styles.chipContainer}>
                  {builderState.teams.map((team, idx) => (
                    <span key={idx} className={styles.chip}>
                      {team}
                      <button
                        type="button"
                        className={styles.chipRemove}
                        onClick={() => removeItem("teams", idx)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Players */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>
                Players (up to {MAX_FILTER_ITEMS})
              </label>
              <div className={styles.chipInputGroup}>
                <input
                  type="text"
                  className={styles.chipInput}
                  value={playerInput}
                  onChange={(e) => setPlayerInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("players", playerInput);
                    }
                  }}
                  placeholder="e.g., Patrick Mahomes"
                  disabled={loading || builderState.players.length >= MAX_FILTER_ITEMS}
                />
                <button
                  type="button"
                  className={styles.addButton}
                  onClick={() => addItem("players", playerInput)}
                  disabled={loading || builderState.players.length >= MAX_FILTER_ITEMS}
                >
                  Add
                </button>
              </div>
              {builderState.players.length > 0 && (
                <div className={styles.chipContainer}>
                  {builderState.players.map((player, idx) => (
                    <span key={idx} className={styles.chip}>
                      {player}
                      <button
                        type="button"
                        className={styles.chipRemove}
                        onClick={() => removeItem("players", idx)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Play Types */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>
                Play Types (up to {MAX_FILTER_ITEMS})
              </label>
              <div className={styles.chipInputGroup}>
                <input
                  type="text"
                  className={styles.chipInput}
                  value={playTypeInput}
                  onChange={(e) => setPlayTypeInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addItem("playTypes", playTypeInput);
                    }
                  }}
                  placeholder="e.g., touchdowns, buzzer beaters"
                  disabled={loading || builderState.playTypes.length >= MAX_FILTER_ITEMS}
                />
                <button
                  type="button"
                  className={styles.addButton}
                  onClick={() => addItem("playTypes", playTypeInput)}
                  disabled={loading || builderState.playTypes.length >= MAX_FILTER_ITEMS}
                >
                  Add
                </button>
              </div>
              <div className={styles.suggestions}>
                {PLAY_TYPE_SUGGESTIONS.slice(0, 5).map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className={styles.suggestionChip}
                    onClick={() => addItem("playTypes", suggestion)}
                    disabled={loading || builderState.playTypes.length >= MAX_FILTER_ITEMS || builderState.playTypes.includes(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
              {builderState.playTypes.length > 0 && (
                <div className={styles.chipContainer}>
                  {builderState.playTypes.map((playType, idx) => (
                    <span key={idx} className={styles.chip}>
                      {playType}
                      <button
                        type="button"
                        className={styles.chipRemove}
                        onClick={() => removeItem("playTypes", idx)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Date Range */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>Time Window</label>
              <div className={styles.datePresets}>
                {DATE_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    className={`${styles.datePresetButton} ${builderState.datePreset === preset.value ? styles.datePresetActive : ""}`}
                    onClick={() => {
                      setBuilderState({ 
                        ...builderState, 
                        datePreset: preset.value,
                        // Clear custom dates when switching away from custom/historical
                        customStartDate: preset.value === "custom" || preset.value === "historical" ? builderState.customStartDate : "",
                        customEndDate: preset.value === "custom" || preset.value === "historical" ? builderState.customEndDate : "",
                      });
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              {(builderState.datePreset === "custom" || builderState.datePreset === "historical") && (
                <div className={styles.dateRange}>
                  <input
                    type="date"
                    className={styles.dateInput}
                    value={builderState.customStartDate}
                    onChange={(e) => setBuilderState({ ...builderState, customStartDate: e.target.value })}
                  />
                  <span className={styles.dateSeparator}>to</span>
                  <input
                    type="date"
                    className={styles.dateInput}
                    value={builderState.customEndDate}
                    onChange={(e) => setBuilderState({ ...builderState, customEndDate: e.target.value })}
                  />
                </div>
              )}
            </div>

            {/* Duration */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>
                Duration: {builderState.durationMinutes} minutes ({Math.round(builderState.durationMinutes / 60 * 10) / 10} hours)
              </label>
              <div className={styles.durationPresets}>
                {[60, 120, 240, 360, 480, 600].map((minutes) => (
                  <button
                    key={minutes}
                    type="button"
                    className={`${styles.durationPreset} ${builderState.durationMinutes === minutes ? styles.durationPresetActive : ""}`}
                    onClick={() => setBuilderState({ ...builderState, durationMinutes: minutes })}
                  >
                    {minutes / 60}h
                  </button>
                ))}
              </div>
              <input
                type="range"
                min="60"
                max="600"
                step="15"
                value={builderState.durationMinutes}
                onChange={(e) => setBuilderState({ ...builderState, durationMinutes: Number(e.target.value) })}
                className={styles.durationSlider}
              />
              <div className={styles.sliderLabels}>
                <span>1 hour</span>
                <span>10 hours</span>
              </div>
            </div>

            {/* Additional Comments */}
            <div className={styles.builderGroup}>
              <label className={styles.builderLabel}>Additional Comments (optional)</label>
              <textarea
                className={styles.commentsInput}
                value={builderState.comments}
                onChange={(e) => setBuilderState({ ...builderState, comments: e.target.value })}
                placeholder="e.g., Focus on official channels, prioritize RedZone-style recaps"
                rows={3}
                disabled={loading}
              />
            </div>

            {/* Submit Button */}
            <button
              className={styles.submitButton}
              onClick={handleSubmit}
              disabled={loading || builderState.sports.length === 0}
            >
              {loading ? "Building Highlight Show..." : "Build Highlight Show"}
            </button>
            <p className={styles.buttonHint}>
              We'll search for highlights uploaded within 48 hours of games. If we can't find enough good clips, we'll tell you.
            </p>
            
            {loading && (
              <div className={styles.loadingContainer}>
                <LoadingSpinner 
                  message={
                    elapsedTime > 30
                      ? `This is taking longer than usual (${elapsedTime}s). Still searching...`
                      : elapsedTime > 10
                      ? `Searching for videos and building your playlist... (${elapsedTime}s)`
                      : "Searching for videos and building your playlist..."
                  }
                />
                {elapsedTime > 15 && (
                  <button
                    className={styles.cancelButton}
                    onClick={handleCancel}
                    type="button"
                  >
                    Cancel Request
                  </button>
                )}
              </div>
            )}
            
            {error && (
              <>
                <ErrorDisplay
                  error={error.message}
                  title={
                    error.code === "NO_VIDEOS_FOUND"
                      ? "No Videos Found"
                      : error.code === "NETWORK_ERROR"
                      ? "Network Error"
                      : "Error Creating Playlist"
                  }
                  onRetry={
                    error.code === "NETWORK_ERROR" || error.code === "NO_VIDEOS_FOUND"
                      ? () => {
                          setError(null);
                          handleSubmit();
                        }
                      : undefined
                  }
                />
                {error.suggestions && error.suggestions.length > 0 && (
                  <div className={styles.suggestions}>
                    <strong>Suggestions:</strong>
                    <ul>
                      {error.suggestions.map((suggestion, idx) => (
                        <li key={idx}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
            
            {successMessage && (
              <div className={styles.success}>
                {successMessage}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
