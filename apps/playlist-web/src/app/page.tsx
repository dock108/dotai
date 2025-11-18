"use client";

import { useMemo, useState } from "react";
import styles from "./page.module.css";
import type {
  EndingDelayChoice,
  LengthBucket,
  PlaylistResult,
} from "@/lib/types";
import { formatDuration } from "@/lib/utils/duration";
import { FEATURE_FLAGS } from "@/lib/constants";
import type { ProgressUpdate } from "@/lib/progress";
import { PROGRESS_MESSAGES } from "@/lib/progress";

const LENGTH_OPTIONS: { value: LengthBucket; label: string }[] = [
  { value: "5_15", label: "5–15 min" },
  { value: "15_30", label: "15–30 min" },
  { value: "30_60", label: "30–60 min" },
  { value: "60_180", label: "1–3 hours" },
  { value: "180_600", label: "3–10 hours" },
  { value: "600_plus", label: "10+ hours" },
];

const ENDING_CHOICES: { value: EndingDelayChoice; label: string }[] = [
  { value: "1h", label: "Reveal after 1 hour" },
  { value: "2h", label: "Reveal after 2 hours" },
  { value: "3h", label: "Reveal after 3 hours" },
  { value: "5h", label: "Reveal after 5 hours" },
  { value: "surprise", label: "Surprise me (60–120 min)" },
];

type FormState = {
  topic: string;
  length: LengthBucket;
  sportsMode: boolean;
  keepEndingHidden: boolean;
  endingDelayChoice: EndingDelayChoice;
};

const DEFAULT_FORM: FormState = {
  topic: "",
  length: FEATURE_FLAGS.LONG_FORM_ONLY ? "600_plus" : "30_60",
  sportsMode: false,
  keepEndingHidden: false,
  endingDelayChoice: "2h",
};

export default function Home() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playlist, setPlaylist] = useState<PlaylistResult | null>(null);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);

  const showEndingToggle =
    FEATURE_FLAGS.LONG_FORM_ONLY || form.length === "600_plus";

  const totalLength = useMemo(() => {
    if (!playlist) return null;
    return formatDuration(playlist.totalDurationSeconds);
  }, [playlist]);

  const handleSubmit = async () => {
    try {
      setError(null);
      setLoading(true);
      setPlaylist(null);
      setProgress({ stage: "parsing_topic", message: PROGRESS_MESSAGES.parsing_topic, progress: 10 });

      // Simulate progress updates (since we can't easily stream from API)
      const progressStages: ProgressUpdate[] = [
        { stage: "parsing_topic", message: PROGRESS_MESSAGES.parsing_topic, progress: 10 },
        { stage: "enhancing_with_rag", message: PROGRESS_MESSAGES.enhancing_with_rag, progress: 25 },
        { stage: "searching_youtube", message: PROGRESS_MESSAGES.searching_youtube, progress: 40 },
        { stage: "analyzing_videos", message: PROGRESS_MESSAGES.analyzing_videos, progress: 60 },
        { stage: "filtering_scoring", message: PROGRESS_MESSAGES.filtering_scoring, progress: 75 },
        { stage: "classifying_videos", message: PROGRESS_MESSAGES.classifying_videos, progress: 85 },
        { stage: "building_playlist", message: PROGRESS_MESSAGES.building_playlist, progress: 95 },
      ];

      let currentStage = 0;
      const progressInterval = setInterval(() => {
        if (currentStage < progressStages.length - 1) {
          currentStage++;
          setProgress(progressStages[currentStage]);
        }
      }, 3000); // Update every 3 seconds

      const response = await fetch("/api/playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: form.topic,
          length: FEATURE_FLAGS.LONG_FORM_ONLY ? "600_plus" : form.length,
          sportsMode: FEATURE_FLAGS.SPORTS_MODE ? form.sportsMode : false,
          keepEndingHidden:
            FEATURE_FLAGS.LONG_FORM_ONLY || showEndingToggle
              ? form.keepEndingHidden
              : false,
          endingDelayChoice: form.keepEndingHidden
            ? form.endingDelayChoice
            : undefined,
        }),
      });

      clearInterval(progressInterval);
      setProgress({ stage: "complete", message: "Complete!", progress: 100 });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Unable to generate playlist.");
      }
      setPlaylist(payload.playlist);
      setProgress(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setProgress(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void handleSubmit();
  };

  const regenerate = () => {
    void handleSubmit();
  };

  return (
    <div className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.hero}>
          <h1>
            {FEATURE_FLAGS.LONG_FORM_ONLY
              ? "Deep-dive playlists for background learning"
              : "AI-curated YouTube playlists"}
          </h1>
          <p className={styles.heroSubtext}>
            {FEATURE_FLAGS.LONG_FORM_ONLY
              ? "10–12 hour flows of explainers, documentaries, and interviews—sequenced for passive learning while you work."
              : "Topic, length, and preferences. We handle the curation."}
          </p>
        </header>

        <div className={styles.grid}>
          <section className={styles.formPanel}>
            <form onSubmit={handleFormSubmit}>
              <label className={styles.label}>
                Topic
                <textarea
                  className={styles.textarea}
                  placeholder={
                    FEATURE_FLAGS.LONG_FORM_ONLY
                      ? 'e.g. "Lufthansa Heist but not Goodfellas" or "History of Bitcoin, exclude price speculation"'
                      : 'e.g. "MH370" or "NBA Lakers 2020 run"'
                  }
                  value={form.topic}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, topic: event.target.value }))
                  }
                  rows={3}
                  required
                />
                {FEATURE_FLAGS.LONG_FORM_ONLY && (
                  <p className={styles.hint}>
                    Describe what you want: "MH370" · "Chernobyl disaster" · "Lufthansa Heist, exclude Goodfellas" · "JFK assassination, no conspiracy theories"
                  </p>
                )}
              </label>

              {FEATURE_FLAGS.LENGTH_SELECTOR && (
                <label className={styles.label}>
                  Length Target
                  <select
                    className={styles.select}
                    value={form.length}
                    onChange={(event) => {
                      const nextLength = event.target.value as LengthBucket;
                      setForm((prev) => ({
                        ...prev,
                        length: nextLength,
                        keepEndingHidden:
                          nextLength === "600_plus"
                            ? prev.keepEndingHidden
                            : false,
                      }));
                    }}
                  >
                    {LENGTH_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {FEATURE_FLAGS.SPORTS_MODE && (
                <div className={styles.toggleRow}>
                  <label className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={form.sportsMode}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          sportsMode: event.target.checked,
                        }))
                      }
                    />
                    <span>Sports Mode → hide spoilers</span>
                  </label>
                </div>
              )}

              {(showEndingToggle || FEATURE_FLAGS.LONG_FORM_ONLY) && (
                <div className={styles.toggleColumn}>
                  <label className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={form.keepEndingHidden}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          keepEndingHidden: event.target.checked,
                        }))
                      }
                    />
                    <span>Keep the ending hidden</span>
                  </label>

                  {form.keepEndingHidden && (
                    <>
                      <label className={styles.label}>
                        When should the outcome first be revealed?
                        <select
                          className={styles.select}
                          value={form.endingDelayChoice}
                          onChange={(event) =>
                            setForm((prev) => ({
                              ...prev,
                              endingDelayChoice:
                                event.target.value as EndingDelayChoice,
                            }))
                          }
                        >
                          {ENDING_CHOICES.map((choice) => (
                            <option key={choice.value} value={choice.value}>
                              {choice.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <p className={styles.hint}>
                        I'll delay major reveals, conclusions, or outcomes until at least this mark. Ending content may appear in a ±90 minute window depending on available videos.
                      </p>
                    </>
                  )}
                </div>
              )}

              <button
                type="submit"
                className={styles.primaryButton}
                disabled={loading}
              >
                {loading ? "Scoring videos…" : FEATURE_FLAGS.LONG_FORM_ONLY ? "Build My 10-Hour Deep Dive" : "Generate Playlist"}
              </button>

              {error && <p className={styles.error}>{error}</p>}
            </form>
          </section>

          <section className={styles.resultsPanel}>
            {loading && progress ? (
              <LoadingCard progress={progress} />
            ) : playlist ? (
              <PlaylistCard
                playlist={playlist}
                totalLength={totalLength}
                loading={loading}
                onRegenerate={regenerate}
              />
            ) : (
              <EmptyState />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function PlaylistCard({
  playlist,
  totalLength,
  loading,
  onRegenerate,
}: {
  playlist: PlaylistResult;
  totalLength: string | null;
  loading: boolean;
  onRegenerate: () => void;
}) {
  const outcomeLockInfo = playlist.endingDelayMinutes
    ? `Outcome locked until: ~${Math.round(playlist.endingDelayMinutes / 60)}h mark`
    : null;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <p className={styles.cardEyebrow}>
            {playlist.playlistLink ? "Live Playlist" : "Preview Only"}
          </p>
          {playlist.playlistLink ? (
            <h2>
              <a
                href={playlist.playlistLink}
                target="_blank"
                rel="noreferrer"
              >
                {playlist.playlistTitle}
              </a>
            </h2>
          ) : (
            <h2>{playlist.playlistTitle}</h2>
          )}
          {totalLength && (
            <p className={styles.runtimeInfo}>
              Total runtime: {totalLength}
              {outcomeLockInfo && <> · {outcomeLockInfo}</>}
            </p>
          )}
        </div>
        {totalLength && <span className={styles.badge}>{totalLength}</span>}
      </div>

      <div className={styles.actions}>
        {playlist.playlistLink ? (
          <a
            className={styles.secondaryButton}
            href={playlist.playlistLink}
            target="_blank"
            rel="noreferrer"
          >
            Open Playlist on YouTube
          </a>
        ) : (
          <div className={styles.note}>
            <p>
              <strong>Playlist not saved to YouTube.</strong>
            </p>
            <p style={{ fontSize: "12px", marginTop: "4px" }}>
              Add <code>YOUTUBE_OAUTH_ACCESS_TOKEN</code> and{" "}
              <code>YOUTUBE_PLAYLIST_CHANNEL_ID</code> to your .env.local to
              auto-create playlists.
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={onRegenerate}
          className={styles.ghostButton}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Generate Alternative Version"}
        </button>
      </div>

      <ol className={styles.videoList}>
        {playlist.segments.map((segment, index) => (
          <li key={segment.video.id} className={styles.videoItem}>
            <div>
              <p className={styles.videoTitle}>
                {index + 1}. {segment.video.title}
              </p>
              <p className={styles.videoMeta}>
                {segment.video.channelTitle} ·{" "}
                {formatDuration(segment.video.durationSeconds)} ·{" "}
                {friendlyTag(segment.video.tag)}
                {typeof segment.startsAtMinute === "number" && (
                  <> · starts at {segment.startsAtMinute}m</>
                )}
              </p>
              {segment.lockedUntilMinute && (
                <p className={styles.locked}>
                  Ending locked until {segment.lockedUntilMinute} min mark.
                </p>
              )}
            </div>
            <a
              href={segment.video.url}
              target="_blank"
              rel="noreferrer"
              className={styles.watchLink}
            >
              Watch
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}

function EmptyState() {
  return (
    <div className={styles.infoCard}>
      <div className={styles.infoContent}>
        <h3 className={styles.infoTitle}>How it works</h3>
        <p>
          Describe any topic—from historical events to true crime mysteries to scientific concepts. 
          Our AI analyzes your request, searches YouTube for relevant content, and uses semantic matching 
          to find videos that actually match what you want to learn, not just keyword matches.
        </p>
        <p>
          {FEATURE_FLAGS.LONG_FORM_ONLY
            ? "We build 10–12 hour playlists sequenced for passive consumption. Videos flow from introductions through deep dives, with optional spoiler protection that delays major reveals until you're ready. Perfect for background learning while working, commuting, or doing chores."
            : "The system filters out low-quality content, penalizes generic list videos, and prioritizes well-produced explainers and documentaries. You get a curated sequence that builds understanding progressively."}
        </p>
        <p>
          {FEATURE_FLAGS.LONG_FORM_ONLY
            ? "You can exclude specific topics (like 'exclude Goodfellas' when searching the Lufthansa Heist) and the system will respect those preferences. The result is a continuous learning experience tailored to your interests."
            : "Each playlist is automatically saved to YouTube (if configured) or shown as a preview. Regenerate anytime to get a different curation of the same topic."}
        </p>
      </div>
    </div>
  );
}

function LoadingCard({ progress }: { progress: ProgressUpdate }) {
  return (
    <div className={styles.card}>
      <div className={styles.loadingCard}>
        <div className={styles.loadingSpinner}></div>
        <h3 className={styles.loadingTitle}>{progress.message}</h3>
        <div className={styles.progressBar}>
          <div
            className={styles.progressFill}
            style={{ width: `${progress.progress}%` }}
          ></div>
        </div>
        <p className={styles.progressText}>{progress.progress}%</p>
      </div>
    </div>
  );
}

function friendlyTag(tag: string) {
  switch (tag) {
    case "intro":
      return "Intro";
    case "context":
      return "Setup";
    case "deep_dive":
      return "Deep Dive";
    case "ending":
      return "Outcome Zone";
    case "misc":
      return "Related Case";
    default:
      return "Bonus";
  }
}

