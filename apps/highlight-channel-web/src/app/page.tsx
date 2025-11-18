"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedSpec, setParsedSpec] = useState<ParsedSpec | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const router = useRouter();

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
    if (!queryText.trim()) return;

    setError(null);
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || "http://localhost:8000";

      const response = await fetch(`${apiUrl}/api/highlights/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_text: queryText,
          mode: "sports_highlight",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to create playlist" }));
        throw new Error(errorData.detail || "Failed to create playlist");
      }

      const data: PlaylistResponse = await response.json();
      
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
          setDurationMinutes(data.explanation.target_duration_minutes);
        }
        setParsedSpec({
          sport: sportMatch?.[1] || "",
          leagues: [],
          teams: [],
          date_range: null,
          content_mix: { highlights: 0.6, bloopers: 0.2, top_plays: 0.2 },
          requested_duration_minutes: data.explanation.target_duration_minutes,
        });
        // Show builder after first successful parse (persist in sessionStorage)
        setShowBuilder(true);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("highlightBuilderShown", "true");
        }
      }
      
      router.push(`/playlist/${data.playlist_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
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
    
    await handleSubmit(builderQuery, false);
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
        </header>

        <div className={styles.mainSection}>
          <div className={styles.inputSection}>
            <label className={styles.label}>
              Describe the sports highlights you want today...
            </label>
            <textarea
              className={styles.textarea}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='e.g., "NFL Week 12 highlights, then MLB bloopers, then any huge upsets from Aug 8, 2010"'
              rows={4}
              disabled={loading}
            />
            <button
              className={styles.submitButton}
              onClick={() => handleSubmit(query)}
              disabled={loading || !query.trim()}
            >
              {loading ? "Building Playlist..." : "Build Playlist"}
            </button>
            {error && <div className={styles.error}>{error}</div>}
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

