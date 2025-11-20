"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient, HighlightsAPI, type HighlightDetailResponse, type APIError, type NetworkError } from "@dock108/js-core";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import styles from "./page.module.css";

interface PlaylistItem {
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
}

interface PlaylistDetail {
  playlist_id: number;
  query_id: number;
  query_text: string;
  items: PlaylistItem[];
  total_duration_seconds: number;
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
  query_metadata: {
    mode: string;
    requested_duration_minutes: number;
    version: number;
    created_at: string;
    last_used_at: string;
  };
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

export default function PlaylistPage() {
  const params = useParams();
  const router = useRouter();
  const playlistId = params.id as string;
  const [playlist, setPlaylist] = useState<HighlightDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [workdayHours, setWorkdayHours] = useState<number | null>(null);
  
  // Initialize API client
  const apiClient = createClient();
  const highlightsAPI = new HighlightsAPI(apiClient);

  useEffect(() => {
    const fetchPlaylist = async () => {
      if (!playlistId) {
        setError({ message: "Invalid playlist ID" });
        setLoading(false);
        return;
      }
      
      const playlistIdNum = parseInt(playlistId, 10);
      if (isNaN(playlistIdNum)) {
        setError({ message: "Invalid playlist ID format" });
        setLoading(false);
        return;
      }
      
      try {
        const data = await highlightsAPI.getPlaylist(playlistIdNum);
        setPlaylist(data);
      } catch (err: unknown) {
        let errorMessage = "Failed to load playlist";
        let errorCode: string | undefined;
        
        if (err instanceof NetworkError) {
          errorCode = "NETWORK_ERROR";
          errorMessage = "Network error. Please check your internet connection and try again.";
        } else if (err instanceof APIError) {
          errorCode = err.statusCode.toString();
          if (err.statusCode === 404) {
            errorMessage = "Playlist not found. It may have been deleted or the ID is incorrect.";
          } else if (err.statusCode >= 500) {
            errorMessage = "Server error. Please try again later.";
          } else {
            errorMessage = err.detail || err.message;
          }
        } else if (err instanceof Error) {
          errorMessage = err.message;
        }
        
        setError({ message: errorMessage, code: errorCode });
      } finally {
        setLoading(false);
      }
    };

    fetchPlaylist();
  }, [playlistId, highlightsAPI]);

  const buildYouTubePlaylistUrl = (items: PlaylistItem[]): string => {
    const videoIds = items.map((item) => item.video_id).join(",");
    return `https://www.youtube.com/watch_videos?video_ids=${videoIds}`;
  };

  const handlePlayAll = () => {
    if (!playlist) return;
    const url = buildYouTubePlaylistUrl(playlist.items);
    window.open(url, "_blank");
  };

  const handleWorkdayMode = (hours: number) => {
    setWorkdayHours(hours);
    // For MVP, just open the playlist - YouTube will handle looping
    if (playlist) {
      const url = buildYouTubePlaylistUrl(playlist.items);
      window.open(url, "_blank");
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <LoadingSpinner message="Loading playlist..." />
        </div>
      </div>
    );
  }

  if (error || !playlist) {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <ErrorDisplay
            error={error?.message || "Playlist not found"}
            title={error?.code === "404" ? "Playlist Not Found" : "Error Loading Playlist"}
            onRetry={
              error?.code !== "404"
                ? () => {
                    setError(null);
                    setLoading(true);
                    const playlistIdNum = parseInt(playlistId, 10);
                    if (!isNaN(playlistIdNum)) {
                      highlightsAPI.getPlaylist(playlistIdNum)
                        .then(setPlaylist)
                        .catch((err) => {
                          setError({
                            message: err instanceof Error ? err.message : "Failed to load playlist",
                            code: err instanceof APIError ? err.statusCode.toString() : undefined,
                          });
                        })
                        .finally(() => setLoading(false));
                    }
                  }
                : undefined
            }
          />
          <button onClick={() => router.push("/")} className={styles.backButton}>
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const totalDuration = formatDuration(playlist.total_duration_seconds);

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <button onClick={() => router.push("/")} className={styles.backButton}>
            ← Back
          </button>
          <h1 className={styles.title}>Your Sports Channel</h1>
          <p className={styles.queryText}>{playlist.query_text || "Sports Highlights"}</p>
          <div className={styles.meta}>
            <span>{playlist.items.length} videos</span>
            <span>•</span>
            <span>{totalDuration} total</span>
            {playlist.cache_status && (
              <>
                <span>•</span>
                <span className={playlist.cache_status === "cached" ? styles.cachedBadge : styles.freshBadge}>
                  {playlist.cache_status === "cached" ? "Cached" : "Fresh"}
                </span>
              </>
            )}
          </div>
        </header>

        <div className={styles.controls}>
          <button className={styles.primaryButton} onClick={handlePlayAll}>
            Play All on YouTube
          </button>
          <div className={styles.workdaySection}>
            <span className={styles.workdayLabel}>Use as background channel for:</span>
            <div className={styles.workdayButtons}>
              {[1, 2, 4, 8].map((hours) => (
                <button
                  key={hours}
                  className={styles.workdayButton}
                  onClick={() => handleWorkdayMode(hours)}
                >
                  {hours}h
                </button>
              ))}
            </div>
            {workdayHours && (
              <p className={styles.workdayNote}>
                Opening YouTube playlist. Enable autoplay and loop in YouTube for {workdayHours}-hour
                background playback.
              </p>
            )}
          </div>
        </div>

        <div className={styles.content}>
          <div className={styles.videoList}>
            <h2 className={styles.sectionTitle}>Videos</h2>
            <ol className={styles.list}>
              {playlist.items.map((item, idx) => (
                <li key={item.video_id} className={styles.videoItem}>
                  <div className={styles.videoNumber}>{idx + 1}</div>
                  <div className={styles.videoContent}>
                    {item.thumbnail_url && (
                      <img
                        src={item.thumbnail_url}
                        alt={item.title}
                        className={styles.thumbnail}
                      />
                    )}
                    <div className={styles.videoInfo}>
                      <h3 className={styles.videoTitle}>{item.title}</h3>
                      <p className={styles.videoMeta}>
                        {item.channel_title} • {formatDuration(item.duration_seconds)} • Score:{" "}
                        {(item.scores.final_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className={styles.watchButton}
                  >
                    Watch
                  </a>
                </li>
              ))}
            </ol>
          </div>

          <div className={styles.explanationPanel}>
            <button
              className={styles.explanationToggle}
              onClick={() => setShowExplanation(!showExplanation)}
            >
              {showExplanation ? "Hide" : "Show"} Explanation
            </button>
            {showExplanation && (
              <div className={styles.explanationContent}>
                <h3 className={styles.explanationTitle}>Why these clips?</h3>

                {playlist.explanation.assumptions.length > 0 && (
                  <div className={styles.explanationSection}>
                    <h4>Assumptions</h4>
                    <ul>
                      {playlist.explanation.assumptions.map((assumption, idx) => (
                        <li key={idx}>{assumption}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className={styles.explanationSection}>
                  <h4>Filters Applied</h4>
                  <p>
                    <strong>Content types:</strong> {playlist.explanation.filters_applied.content_types.join(", ")}
                  </p>
                  {playlist.explanation.filters_applied.exclusions.length > 0 && (
                    <p>
                      <strong>Exclusions:</strong> {playlist.explanation.filters_applied.exclusions.join(", ")}
                    </p>
                  )}
                  <p>
                    <strong>NSFW filter:</strong> {playlist.explanation.filters_applied.nsfw_filter ? "Yes" : "No"}
                  </p>
                </div>

                <div className={styles.explanationSection}>
                  <h4>Ranking Factors</h4>
                  <p>
                    Videos were scored using:
                  </p>
                  <ul>
                    <li>
                      Highlight keywords:{" "}
                      {(playlist.explanation.ranking_factors.highlight_score_weight * 100).toFixed(0)}%
                    </li>
                    <li>
                      Channel reputation:{" "}
                      {(playlist.explanation.ranking_factors.channel_reputation_weight * 100).toFixed(0)}%
                    </li>
                    <li>
                      View count:{" "}
                      {(playlist.explanation.ranking_factors.view_count_weight * 100).toFixed(0)}%
                    </li>
                    <li>
                      Freshness:{" "}
                      {(playlist.explanation.ranking_factors.freshness_weight * 100).toFixed(0)}%
                    </li>
                  </ul>
                </div>

                {playlist.explanation.coverage_notes.length > 0 && (
                  <div className={styles.explanationSection}>
                    <h4>Coverage Notes</h4>
                    <ul>
                      {playlist.explanation.coverage_notes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className={styles.explanationSection}>
                  <h4>Statistics</h4>
                  <p>
                    Found {playlist.explanation.total_candidates} candidate videos, selected{" "}
                    {playlist.explanation.selected_videos} to reach{" "}
                    {playlist.explanation.actual_duration_minutes} minutes (target:{" "}
                    {playlist.explanation.target_duration_minutes} minutes).
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

