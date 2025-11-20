"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient, HighlightsAPI, type HighlightPlanResponse, type APIError, type NetworkError } from "@dock108/js-core";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import styles from "./page.module.css";

const PRESETS = [
  { text: "Last night's NFL", query: "NFL highlights from last night" },
  { text: "Today's MLB", query: "MLB highlights from today" },
  { text: "Random bloopers", query: "sports bloopers from this week" },
  { text: "Deep dive on one team", query: "Kansas City Chiefs highlights from this season" },
];

const SPORTS = ["NFL", "NBA", "MLB", "NHL", "Soccer", "Golf", "F1"];

interface ParsedSpec {
  sport: string;
  leagues: string[];
  teams: string[];
  date_range: {
    start_date?: string;
    end_date?: string;
    single_date?: string;
  } | null;
  content_mix: {
    highlights: number;
    bloopers: number;
    top_plays: number;
  };
  requested_duration_minutes: number;
}

interface PlaylistResponse {
  playlist_id: number;
  query_id: number;
  items: Array<{
    video_id: string;
    title: string;
    channel_title: string;
    duration_seconds: number;
    url: string;
    thumbnail_url?: string;
    scores: {
      final_score: number;
      highlight_score: number;
      channel_reputation: number;
      view_count_normalized: number;
      freshness_score: number;
    };
  }>;
  total_duration_seconds: number;
  cache_status: string;
  explanation: {
    assumptions: string[];
    filters_applied: {
      content_types: string[];
      exclusions: string[];
      nsfw_filter: boolean;
    };
    ranking_factors: {
      highlight_score_weight: number;
      channel_reputation_weight: number;
      view_count_weight: number;
      freshness_weight: number;
    };
    coverage_notes: string[];
    total_candidates: number;
    selected_videos: number;
    actual_duration_minutes: number;
    target_duration_minutes: number;
  };
  created_at: string;
  stale_after: string | null;
}

interface ErrorInfo {
  code?: string;
  message: string;
  detail?: string;
  suggestions?: string[];
  retry_after?: number;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [parsedSpec, setParsedSpec] = useState<ParsedSpec | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [requestStartTime, setRequestStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const router = useRouter();
  
  // Initialize API client
  const apiClient = createClient();
  const highlightsAPI = new HighlightsAPI(apiClient);
  
  const EXAMPLE_QUERIES = [
    "NFL highlights from last night, 30 minutes",
    "NBA top plays from this week",
    "MLB bloopers from September 2024",
    "NHL highlights from yesterday, 1 hour",
    "Kansas City Chiefs highlights from this season",
    "Sports upsets from last month",
  ];
  
  const TIPS = [
    "Be specific about the sport (NFL, NBA, MLB, etc.)",
    "Include a time period (last night, this week, specific date)",
    "Specify content type (highlights, bloopers, top plays)",
    "Request a duration (15 minutes to 8 hours)",
    "You can combine multiple requests (e.g., 'NFL then MLB highlights')",
  ];

  // Check if builder should be shown (from sessionStorage)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const builderShown = sessionStorage.getItem("highlightBuilderShown");
      if (builderShown === "true") {
        setShowBuilder(true);
      }
    }
  }, []);

  // Query builder state
  const [selectedSport, setSelectedSport] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [durationMinutes, setDurationMinutes] = useState<number>(60);
  const [contentMix, setContentMix] = useState<number>(0.5); // 0 = bloopers, 1 = highlights

  const handleSubmit = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed) {
      setError({ message: "Please enter a query" });
      return;
    }
    
    if (trimmed.length < 5) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Query must be at least 5 characters long",
        suggestions: ["Try adding more details about the sport, date, or content type"],
      });
      return;
    }
    
    if (trimmed.length > 500) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Query is too long (max 500 characters)",
        suggestions: ["Try shortening your query or breaking it into multiple requests"],
      });
      return;
    }

    setError(null);
    setSuccessMessage(null);
    setLoading(true);
    const startTime = Date.now();
    setRequestStartTime(startTime);
    setElapsedTime(0);
    
    // Start elapsed time counter
    const timeInterval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    
    // Create abort controller for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const data = await highlightsAPI.planPlaylist({
        query_text: queryText,
        mode: "sports_highlight",
      });
      
      // Extract spec from explanation for builder
      if (data.explanation) {
        // Store parsed spec for builder
        const sportMatch = queryText.match(/\b(NFL|NBA|MLB|NHL|Soccer|Golf|F1)\b/i);
        if (sportMatch) {
          setSelectedSport(sportMatch[1].toUpperCase());
        }
        // Extract duration if available
        const durationMatch = queryText.match(/(\d+)\s*(?:hours?|hrs?|minutes?|mins?)/i);
        if (durationMatch) {
          const num = parseInt(durationMatch[1]);
          if (queryText.toLowerCase().includes("hour")) {
            setDurationMinutes(num * 60);
          } else {
            setDurationMinutes(num);
          }
        } else {
          setDurationMinutes(data.explanation.target_duration_minutes || 60);
        }
        setParsedSpec({
          sport: sportMatch?.[1] || "",
          leagues: [],
          teams: [],
          date_range: null,
          content_mix: { highlights: 0.6, bloopers: 0.2, top_plays: 0.2 },
          requested_duration_minutes: data.explanation.target_duration_minutes || 60,
        });
        // Show builder after first successful parse (persist in sessionStorage)
        setShowBuilder(true);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("highlightBuilderShown", "true");
        }
      }
      
      // Handle empty results
      if (data.items.length === 0) {
        setError({
          code: "NO_VIDEOS_FOUND",
          message: "No videos found matching your request.",
          detail: "We couldn't find any videos that match your search criteria.",
          suggestions: [
            "Try a broader search (e.g., 'NFL highlights' instead of specific teams)",
            "Adjust the date range or remove date filters",
            "Check if the sport/league name is spelled correctly",
            "Try a more general query",
          ],
        });
        setLoading(false);
        return;
      }
      
      // Show success message
      const cacheStatus = data.cache_status === "cached" ? "from cache" : "fresh";
      const videoCount = data.items.length;
      const durationMinutes = Math.round(data.total_duration_seconds / 60);
      setSuccessMessage(
        `Playlist created! Found ${videoCount} videos (${durationMinutes} minutes, ${cacheStatus}). Redirecting...`
      );
      
      // Clear intervals and abort controller
      clearInterval(timeInterval);
      setAbortController(null);
      setRequestStartTime(null);
      
      // Small delay to show success message, then redirect
      setTimeout(() => {
        router.push(`/playlist/${data.playlist_id}`);
      }, 1000);
    } catch (err: unknown) {
      // Clear intervals and abort controller
      clearInterval(timeInterval);
      setAbortController(null);
      setRequestStartTime(null);
      let errorInfo: ErrorInfo = {
        message: "Something went wrong. Please try again.",
      };
      
      if (err instanceof NetworkError) {
        errorInfo = {
          code: "NETWORK_ERROR",
          message: "Network error. Please check your internet connection and try again.",
          detail: err.message,
          suggestions: [
            "Check your internet connection",
            "Try refreshing the page",
            "If using a VPN, try disconnecting it",
          ],
        };
      } else if (err instanceof APIError) {
        // Try to parse error detail as JSON (if it's our structured error)
        try {
          const errorData = typeof err.detail === "string" ? JSON.parse(err.detail) : err.detail;
          errorInfo = {
            code: errorData.error_code || err.statusCode.toString(),
            message: errorData.message || err.message,
            detail: errorData.detail,
            suggestions: errorData.suggestions,
            retry_after: errorData.retry_after,
          };
        } catch {
          // If parsing fails, use the error message directly
          errorInfo = {
            code: err.statusCode.toString(),
            message: err.detail || err.message,
          };
        }
      } else if (err instanceof Error) {
        errorInfo = {
          message: err.message,
        };
      }
      
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
    setError({
      code: "CANCELLED",
      message: "Request cancelled",
    });
  };

  const handleBuilderUpdate = async () => {
    // Construct query from builder state
    const parts: string[] = [];
    if (selectedSport) parts.push(selectedSport);
    if (startDate && endDate) {
      parts.push(`from ${startDate} to ${endDate}`);
    } else if (startDate) {
      parts.push(`from ${startDate}`);
    }
    if (contentMix < 0.3) {
      parts.push("bloopers");
    } else if (contentMix > 0.7) {
      parts.push("highlights");
    } else {
      parts.push("highlights and bloopers");
    }
    parts.push(`${durationMinutes} minutes`);
    const builderQuery = parts.join(" ");
    
    await handleSubmit(builderQuery);
  };

  const handlePreset = (presetQuery: string) => {
    setQuery(presetQuery);
    handleSubmit(presetQuery);
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <header className={styles.hero}>
          <h1 className={styles.title}>Build Your Own Sports Channel</h1>
          <p className={styles.subtitle}>
            Describe the sports highlights you want, and we'll build a custom playlist for you.
          </p>
          <button
            className={styles.helpToggle}
            onClick={() => setShowHelp(!showHelp)}
            type="button"
          >
            {showHelp ? "Hide" : "Show"} Tips & Examples
          </button>
        </header>
        
        {showHelp && (
          <div className={styles.helpSection}>
            <div className={styles.helpContent}>
              <h3 className={styles.helpTitle}>How It Works</h3>
              <p className={styles.helpText}>
                Just describe what you want in natural language. We'll search YouTube for the best videos
                matching your request and create a custom playlist. The more specific you are, the better results you'll get.
              </p>
              
              <h3 className={styles.helpTitle}>Example Queries</h3>
              <div className={styles.exampleQueries}>
                {EXAMPLE_QUERIES.map((example, idx) => (
                  <button
                    key={idx}
                    className={styles.exampleQuery}
                    onClick={() => {
                      setQuery(example);
                      setShowHelp(false);
                    }}
                    type="button"
                  >
                    "{example}"
                  </button>
                ))}
              </div>
              
              <h3 className={styles.helpTitle}>Tips for Better Results</h3>
              <ul className={styles.tipsList}>
                {TIPS.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
              
              <div className={styles.disclaimer}>
                <strong>Note:</strong> This app builds playlists using public YouTube videos. We do not host or control the content.
              </div>
            </div>
          </div>
        )}

        <div className={styles.mainSection}>
          <div className={styles.inputSection}>
            <label className={styles.label}>
              Describe the sports highlights you want today...
            </label>
            <textarea
              className={styles.textarea}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                // Clear error when user starts typing
                if (error) {
                  setError(null);
                }
                // Real-time validation feedback
                const text = e.target.value.trim();
                if (text.length > 0 && text.length < 5) {
                  // Show hint but don't block
                }
              }}
              placeholder='e.g., "NFL Week 12 highlights, then MLB bloopers, then any huge upsets from Aug 8, 2010"'
              rows={4}
              disabled={loading}
              maxLength={500}
            />
            {query.length > 0 && query.length < 5 && (
              <div className={styles.validationHint}>
                Query must be at least 5 characters (currently {query.length})
              </div>
            )}
            {query.length >= 500 && (
              <div className={styles.validationWarning}>
                Query is too long (max 500 characters)
              </div>
            )}
            <button
              className={styles.submitButton}
              onClick={() => handleSubmit(query)}
              disabled={loading || !query.trim()}
            >
              {loading ? "Building Playlist..." : "Build Playlist"}
            </button>
            
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
                      : error.code === "RATE_LIMIT_EXCEEDED"
                      ? "Rate Limit Exceeded"
                      : error.code === "QUOTA_EXCEEDED"
                      ? "Service Temporarily Unavailable"
                      : error.code === "NETWORK_ERROR"
                      ? "Network Error"
                      : "Error Creating Playlist"
                  }
                  onRetry={
                    error.code === "RATE_LIMIT_EXCEEDED" ||
                    error.code === "NETWORK_ERROR" ||
                    error.code === "NO_VIDEOS_FOUND"
                      ? () => {
                          setError(null);
                          handleSubmit(query);
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
                {error.retry_after && (
                  <div className={styles.retryInfo}>
                    Please wait {Math.ceil(error.retry_after / 60)} minutes before trying again.
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

          <div className={styles.presetsSection}>
            <p className={styles.presetsLabel}>Quick presets:</p>
            <div className={styles.presets}>
              {PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  className={styles.presetChip}
                  onClick={() => handlePreset(preset.query)}
                  disabled={loading}
                >
                  {preset.text}
                </button>
              ))}
            </div>
          </div>

          {showBuilder && parsedSpec && (
            <div className={styles.builderSection}>
              <h3 className={styles.builderTitle}>Refine Your Request</h3>
              
              <div className={styles.builderGroup}>
                <label className={styles.builderLabel}>Sport</label>
                <div className={styles.sportChips}>
                  {SPORTS.map((sport) => (
                    <button
                      key={sport}
                      className={`${styles.sportChip} ${selectedSport === sport ? styles.sportChipActive : ""}`}
                      onClick={() => {
                        setSelectedSport(sport);
                        handleBuilderUpdate();
                      }}
                    >
                      {sport}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.builderGroup}>
                <label className={styles.builderLabel}>Date Range</label>
                <div className={styles.dateRange}>
                  <input
                    type="date"
                    className={styles.dateInput}
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      if (e.target.value && endDate) {
                        handleBuilderUpdate();
                      }
                    }}
                  />
                  <span className={styles.dateSeparator}>to</span>
                  <input
                    type="date"
                    className={styles.dateInput}
                    value={endDate}
                    onChange={(e) => {
                      setEndDate(e.target.value);
                      if (startDate && e.target.value) {
                        handleBuilderUpdate();
                      }
                    }}
                  />
                </div>
              </div>

              <div className={styles.builderGroup}>
                <label className={styles.builderLabel}>
                  Duration: {durationMinutes} minutes ({Math.round(durationMinutes / 60 * 10) / 10} hours)
                </label>
                <input
                  type="range"
                  min="15"
                  max="480"
                  step="15"
                  value={durationMinutes}
                  onChange={(e) => {
                    setDurationMinutes(Number(e.target.value));
                  }}
                  onMouseUp={handleBuilderUpdate}
                  onTouchEnd={handleBuilderUpdate}
                  className={styles.durationSlider}
                />
                <div className={styles.sliderLabels}>
                  <span>15 min</span>
                  <span>8 hours</span>
                </div>
              </div>

              <div className={styles.builderGroup}>
                <label className={styles.builderLabel}>
                  Content Mix: {contentMix < 0.3 ? "Bloopers" : contentMix > 0.7 ? "Highlights" : "Mixed"}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={contentMix}
                  onChange={(e) => {
                    setContentMix(Number(e.target.value));
                  }}
                  onMouseUp={handleBuilderUpdate}
                  onTouchEnd={handleBuilderUpdate}
                  className={styles.contentSlider}
                />
                <div className={styles.sliderLabels}>
                  <span>Bloopers</span>
                  <span>Highlights</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className={styles.promoSection}>
          <p className={styles.promoText}>
            Not getting the results you expect when you talk to AI?{" "}
            <a href="/game" className={styles.promoLink}>
              Try our AI Prompting Game (iOS / Web)
            </a>{" "}
            – learn to describe what you actually want.
          </p>
        </div>
      </div>
    </div>
  );
}

