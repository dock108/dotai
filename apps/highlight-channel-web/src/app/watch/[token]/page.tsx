"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient, HighlightsAPI, type HighlightDetailResponse, APIError, NetworkError } from "@dock108/js-core";
import { LoadingSpinner, ErrorDisplay } from "@dock108/ui-kit";
import styles from "./page.module.css";
import type { PlaylistItem } from "@/lib/types";
import { formatDuration, extractErrorInfo } from "@/lib/utils";

// YouTube iframe API types
declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady: () => void;
  }
}

export default function WatchPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;
  const [playlist, setPlaylist] = useState<HighlightDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(100);
  const [progress, setProgress] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [expiresIn, setExpiresIn] = useState<string>("");
  
  const playerRef = useRef<any>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const expiryIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const apiClient = createClient();
  const highlightsAPI = new HighlightsAPI(apiClient);

  // Load playlist data
  useEffect(() => {
    const fetchPlaylist = async () => {
      if (!token) {
        setError({ message: "Invalid watch token" });
        setLoading(false);
        return;
      }
      
      try {
        const data = await highlightsAPI.getPlaylistByToken(token);
        setPlaylist(data);
        
        // Calculate expiration countdown
        if (data.query_metadata) {
          // Token expires 48 hours after generation, but we don't have that timestamp
          // For now, show a generic message
          setExpiresIn("48 hours");
        }
      } catch (err: unknown) {
        const errorInfo = extractErrorInfo(err);
        if (errorInfo.code === "403" || (err instanceof APIError && err.statusCode === 403)) {
          setError({ 
            message: "This watch link has expired or is invalid. Generate a new link from the playlist page.",
            code: "TOKEN_EXPIRED" 
          });
        } else if (errorInfo.code === "404" || (err instanceof APIError && err.statusCode === 404)) {
          setError({ message: "Playlist not found.", code: "404" });
        } else {
          setError({ message: errorInfo.message || "Failed to load playlist", code: errorInfo.code });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPlaylist();
  }, [token]);

  // Load YouTube iframe API
  useEffect(() => {
    if (!playlist || playlist.items.length === 0) return;

    const loadYouTubeAPI = () => {
      if (window.YT && window.YT.Player) {
        initializePlayer();
        return;
      }

      // Load the API script
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      const firstScriptTag = document.getElementsByTagName("script")[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

      window.onYouTubeIframeAPIReady = () => {
        initializePlayer();
      };
    };

    const initializePlayer = () => {
      if (!playerContainerRef.current || !playlist) return;

      const currentVideo = playlist.items[currentVideoIndex];
      if (!currentVideo) return;

      playerRef.current = new window.YT.Player(playerContainerRef.current, {
        videoId: currentVideo.video_id,
        playerVars: {
          autoplay: 1,
          controls: 1,
          rel: 0,
          modestbranding: 1,
        },
        events: {
          onReady: (event: any) => {
            event.target.setVolume(volume);
            event.target.playVideo();
            setIsPlaying(true);
            startProgressTracking();
          },
          onStateChange: (event: any) => {
            // YT.PlayerState.ENDED = 0
            if (event.data === 0) {
              handleVideoEnd();
            }
            // YT.PlayerState.PLAYING = 1
            if (event.data === 1) {
              setIsPlaying(true);
            }
            // YT.PlayerState.PAUSED = 2
            if (event.data === 2) {
              setIsPlaying(false);
            }
          },
        },
      });
    };

    loadYouTubeAPI();

    return () => {
      if (playerRef.current) {
        try {
          playerRef.current.destroy();
        } catch (e) {
          // Ignore errors during cleanup
        }
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [playlist, currentVideoIndex]);

  // Update player when video index changes
  useEffect(() => {
    if (playerRef.current && playlist && playlist.items[currentVideoIndex]) {
      const currentVideo = playlist.items[currentVideoIndex];
      playerRef.current.loadVideoById(currentVideo.video_id);
      setIsPlaying(true);
    }
  }, [currentVideoIndex, playlist]);

  const startProgressTracking = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    
    progressIntervalRef.current = setInterval(() => {
      if (playerRef.current && playerRef.current.getCurrentTime && playerRef.current.getDuration) {
        try {
          const currentTime = playerRef.current.getCurrentTime();
          const duration = playerRef.current.getDuration();
          if (duration > 0) {
            setProgress((currentTime / duration) * 100);
            setTimeRemaining(duration - currentTime);
          }
        } catch (e) {
          // Ignore errors
        }
      }
    }, 1000);
  };

  const handleVideoEnd = () => {
    if (!playlist) return;
    
    const nextIndex = currentVideoIndex + 1;
    if (nextIndex >= playlist.items.length) {
      // Loop back to beginning
      setCurrentVideoIndex(0);
    } else {
      setCurrentVideoIndex(nextIndex);
    }
  };

  const handlePlayPause = () => {
    if (!playerRef.current) return;
    
    if (isPlaying) {
      playerRef.current.pauseVideo();
    } else {
      playerRef.current.playVideo();
    }
  };

  const handleNext = () => {
    if (!playlist) return;
    const nextIndex = (currentVideoIndex + 1) % playlist.items.length;
    setCurrentVideoIndex(nextIndex);
  };

  const handlePrevious = () => {
    if (!playlist) return;
    const prevIndex = currentVideoIndex === 0 ? playlist.items.length - 1 : currentVideoIndex - 1;
    setCurrentVideoIndex(prevIndex);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseInt(e.target.value, 10);
    setVolume(newVolume);
    if (playerRef.current && playerRef.current.setVolume) {
      playerRef.current.setVolume(newVolume);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekPercent = parseFloat(e.target.value);
    if (playerRef.current && playerRef.current.getDuration && playerRef.current.seekTo) {
      try {
        const duration = playerRef.current.getDuration();
        const seekTime = (seekPercent / 100) * duration;
        playerRef.current.seekTo(seekTime, true);
        setProgress(seekPercent);
      } catch (e) {
        // Ignore errors
      }
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
            title={error?.code === "TOKEN_EXPIRED" ? "Link Expired" : "Error Loading Playlist"}
            onRetry={
              error?.code !== "TOKEN_EXPIRED" && error?.code !== "404"
                ? () => {
                    setError(null);
                    setLoading(true);
                    highlightsAPI.getPlaylistByToken(token)
                      .then(setPlaylist)
                      .catch((err) => {
                        setError({
                          message: err instanceof Error ? err.message : "Failed to load playlist",
                          code: err instanceof APIError ? err.statusCode.toString() : undefined,
                        });
                      })
                      .finally(() => setLoading(false));
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

  const currentVideo = playlist.items[currentVideoIndex];
  const totalVideos = playlist.items.length;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.header}>
          <button onClick={() => router.push("/")} className={styles.backButton}>
            ← Back
          </button>
          <h1 className={styles.title}>{playlist.query_text || "Highlight Show"}</h1>
          <p className={styles.subtitle}>
            Video {currentVideoIndex + 1} of {totalVideos} • {formatDuration(playlist.total_duration_seconds)}
          </p>
          {expiresIn && (
            <p className={styles.expiryNotice}>Link expires in {expiresIn}</p>
          )}
        </div>

        <div className={styles.playerSection}>
          <div className={styles.playerContainer}>
            <div ref={playerContainerRef} className={styles.youtubePlayer}></div>
          </div>

          {currentVideo && (
            <div className={styles.videoInfo}>
              <h2 className={styles.videoTitle}>{currentVideo.title}</h2>
              <p className={styles.videoMeta}>
                {currentVideo.channel_title} • {formatDuration(currentVideo.duration_seconds)}
              </p>
            </div>
          )}

          <div className={styles.controls}>
            <div className={styles.controlRow}>
              <button className={styles.controlButton} onClick={handlePlayPause}>
                {isPlaying ? "⏸ Pause" : "▶ Play"}
              </button>
              <button className={styles.controlButton} onClick={handlePrevious} disabled={totalVideos === 1}>
                ⏮ Previous
              </button>
              <button className={styles.controlButton} onClick={handleNext} disabled={totalVideos === 1}>
                Next ⏭
              </button>
              <div className={styles.volumeControl}>
                <label>🔊</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volume}
                  onChange={handleVolumeChange}
                  className={styles.volumeSlider}
                />
                <span>{volume}%</span>
              </div>
            </div>

            <div className={styles.progressControl}>
              <input
                type="range"
                min="0"
                max="100"
                value={progress}
                onChange={handleSeek}
                className={styles.progressSlider}
              />
              <div className={styles.progressLabels}>
                <span>{formatDuration(Math.floor(timeRemaining))}</span>
                <span>{formatDuration(currentVideo?.duration_seconds || 0)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.playlistInfo}>
          <h3 className={styles.playlistTitle}>Playlist ({totalVideos} videos)</h3>
          <div className={styles.playlistList}>
            {playlist.items.map((item, idx) => (
              <div
                key={item.video_id}
                className={`${styles.playlistItem} ${idx === currentVideoIndex ? styles.playlistItemActive : ""}`}
                onClick={() => setCurrentVideoIndex(idx)}
              >
                <span className={styles.playlistNumber}>{idx + 1}</span>
                <div className={styles.playlistItemContent}>
                  <h4 className={styles.playlistItemTitle}>{item.title}</h4>
                  <p className={styles.playlistItemMeta}>
                    {item.channel_title} • {formatDuration(item.duration_seconds)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

