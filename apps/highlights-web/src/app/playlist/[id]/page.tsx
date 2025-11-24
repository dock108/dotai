"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient, HighlightsAPI, type HighlightDetailResponse, APIError, NetworkError } from "@dock108/js-core";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import styles from "./page.module.css";
import type { PlaylistItem, PlaylistDetail } from "@/lib/types";
import { formatDuration, extractErrorInfo } from "@/lib/utils";

/**
 * Playlist detail page component.
 * 
 * Displays a generated highlight playlist with:
 * - Video list with scores and metadata
 * - Explanation panel showing assumptions, filters, and ranking factors
 * - Workday mode configuration (1h, 2h, 4h, 8h loops)
 * - Watch token generation for temporary YouTube playlist access
 * 
 * Fetches playlist data via GET /api/highlights/{playlist_id} on mount.
 */
export default function PlaylistPage() {
  const params = useParams();
  const router = useRouter();
  const playlistId = params.id as string;
  const [playlist, setPlaylist] = useState<HighlightDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [workdayHours, setWorkdayHours] = useState<number | null>(null);
  const [watchToken, setWatchToken] = useState<{token: string; watch_url: string; expires_at: string} | null>(null);
  const [generatingToken, setGeneratingToken] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  
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
        const errorInfo = extractErrorInfo(err);
        // Provide more specific messages for common cases
        if (errorInfo.code === "404" || (err instanceof APIError && err.statusCode === 404)) {
          setError({ message: "Playlist not found. It may have been deleted or the ID is incorrect.", code: "404" });
        } else if (errorInfo.code === "NETWORK_ERROR" || err instanceof NetworkError) {
          setError({ message: "Network error. Please check your internet connection and try again.", code: "NETWORK_ERROR" });
        } else {
          setError({ message: errorInfo.message || "Failed to load playlist", code: errorInfo.code });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPlaylist();
  }, [playlistId]); // Only refetch when playlistId changes

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

  const handleGenerateWatchLink = async () => {
    if (!playlist) return;
    
    setGeneratingToken(true);
    setTokenError(null);
    
    try {
      const tokenData = await highlightsAPI.getWatchToken(playlist.playlist_id);
      setWatchToken(tokenData);
    } catch (err: unknown) {
      const errorInfo = extractErrorInfo(err);
      setTokenError(errorInfo.message || "Failed to generate watch link");
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleCopyWatchLink = () => {
    if (!watchToken) return;
    
    const fullUrl = `${window.location.origin}${watchToken.watch_url}`;
    navigator.clipboard.writeText(fullUrl).then(() => {
      // Show brief success feedback
      const button = document.querySelector(`[data-copy-button]`) as HTMLButtonElement;
      if (button) {
        const originalText = button.textContent;
        button.textContent = "Copied!";
        setTimeout(() => {
          button.textContent = originalText;
        }, 2000);
      }
    });
  };

  const formatTimeUntilExpiry = (expiresAt: string): string => {
    try {
      const expiry = new Date(expiresAt);
      const now = new Date();
      const hoursUntil = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60));
      if (hoursUntil < 1) {
        const minutesUntil = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60));
        return `${minutesUntil} minutes`;
      }
      return `${hoursUntil} hours`;
    } catch {
      return "48 hours";
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
  const actualMinutes = playlist.explanation.actual_duration_minutes;
  const targetMinutes = playlist.explanation.target_duration_minutes;
  const isShort = actualMinutes < targetMinutes * 0.5;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.heroSection}>
          <button onClick={() => router.push("/")} className={styles.backButton}>
            ← Back
          </button>
          <header className={styles.header}>
            <h1 className={styles.title}>Your Highlight Show</h1>
            <p className={styles.subtitle}>
              {playlist.query_text || "Sports Highlights"} • {playlist.items.length} videos • {totalDuration}
            </p>
            {isShort && (
              <div className={styles.coverageBanner}>
                We could only find {actualMinutes.toFixed(1)} minutes of strong clips for this request (goal: {targetMinutes} minutes). 
                Try widening the date range or combining multiple sports.
              </div>
            )}
          </header>
        </div>

        <div className={styles.controls}>
          <div className={styles.buttonGroup}>
            <button className={styles.primaryButton} onClick={handlePlayAll}>
              Play Show on YouTube
            </button>
            <button 
              className={styles.secondaryButton} 
              onClick={handleGenerateWatchLink}
              disabled={generatingToken || !!watchToken}
            >
              {generatingToken ? "Generating..." : watchToken ? "Watch Link Generated" : "Generate Watch Link"}
            </button>
          </div>
          {tokenError && (
            <p className={styles.errorText}>{tokenError}</p>
          )}
          {watchToken && (
            <div className={styles.watchLinkSection}>
              <div className={styles.watchLinkBox}>
                <input
                  type="text"
                  readOnly
                  value={`${window.location.origin}${watchToken.watch_url}`}
                  className={styles.watchLinkInput}
                />
                <button
                  data-copy-button
                  className={styles.copyButton}
                  onClick={handleCopyWatchLink}
                >
                  Copy Link
                </button>
              </div>
              <p className={styles.expiryText}>
                Link expires in {formatTimeUntilExpiry(watchToken.expires_at)}
              </p>
            </div>
          )}
          <p className={styles.playHint}>
            Starts a playlist that will loop when it finishes.
          </p>
          <div className={styles.lengthSection}>
            <span className={styles.lengthLabel}>Run this show for:</span>
            <div className={styles.lengthButtons}>
              {[30, 60, 120, 240, 480].map((minutes) => {
                const hours = minutes / 60;
                const label = hours >= 1 ? `${hours}h` : `${minutes}m`;
                return (
                  <button
                    key={minutes}
                    className={styles.lengthButton}
                    onClick={() => handleWorkdayMode(hours)}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            {workdayHours && (
              <p className={styles.lengthNote}>
                Opening YouTube playlist. Enable autoplay and loop in YouTube for {workdayHours}-hour
                background playback.
              </p>
            )}
          </div>
        </div>

        <div className={styles.content}>
          <div className={styles.videoList}>
            <h2 className={styles.sectionTitle}>Videos in this Highlight Show</h2>
            <div className={styles.playlistTotal}>
              Total: {playlist.items.length} videos • {totalDuration} (Goal: {Math.round(playlist.explanation.target_duration_minutes)} minutes)
            </div>
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
                        {item.channel_title} • {formatDuration(item.duration_seconds)}
                      </p>
                      <div className={styles.scoreBadge}>
                        Score: {(item.scores.final_score * 100).toFixed(0)}%
                      </div>
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
              {showExplanation ? "Hide" : "Why these videos?"}
            </button>
            {showExplanation && (
              <div className={styles.explanationContent}>
                <h3 className={styles.explanationTitle}>How we built this show</h3>
                <p className={styles.explanationIntro}>
                  We searched YouTube for videos that match your request and scored each one based on relevance, 
                  quality, and recency. The highest-scoring clips were added to your highlight show until we hit your target length.
                </p>

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
                  <h4>Score Breakdown</h4>
                  <div className={styles.scoreBreakdown}>
                    <div className={styles.scoreItem}>
                      <span className={styles.scoreLabel}>Relevance to prompt (sport, team, player):</span>
                      <span className={styles.scoreValue}>40%</span>
                    </div>
                    <div className={styles.scoreItem}>
                      <span className={styles.scoreLabel}>Highlight keywords ("top plays", "highlights", etc.):</span>
                      <span className={styles.scoreValue}>25%</span>
                    </div>
                    <div className={styles.scoreItem}>
                      <span className={styles.scoreLabel}>Channel quality (reputation, posting history):</span>
                      <span className={styles.scoreValue}>20%</span>
                    </div>
                    <div className={styles.scoreItem}>
                      <span className={styles.scoreLabel}>Freshness (how recent):</span>
                      <span className={styles.scoreValue}>15%</span>
                    </div>
                  </div>
                </div>

                {playlist.explanation.coverage_notes.length > 0 && (
                  <div className={styles.explanationSection}>
                    <h4>Coverage Notes</h4>
                    <p>
                      We found {playlist.explanation.selected_videos} strong candidates for this request, 
                      totaling {playlist.explanation.actual_duration_minutes.toFixed(1)} minutes. 
                      To reach your {playlist.explanation.target_duration_minutes}-minute target, you could:
                    </p>
                    <ul>
                      {playlist.explanation.coverage_notes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className={styles.explanationSection}>
                  <h4>Stats</h4>
                  <p>
                    Videos considered: {playlist.explanation.total_candidates}
                  </p>
                  <p>
                    Selected: {playlist.explanation.selected_videos}
                  </p>
                  <p>
                    Total runtime: {playlist.explanation.actual_duration_minutes.toFixed(1)} minutes 
                    (Target: {playlist.explanation.target_duration_minutes} minutes)
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

