"use client";

import { useMemo, useState } from "react";
import styles from "./page.module.css";
import type {
  EndingDelayChoice,
  LengthBucket,
  PlaylistResult,
} from "@/lib/types";
import { formatDuration } from "@/lib/utils/duration";

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
  length: "30_60",
  sportsMode: false,
  keepEndingHidden: false,
  endingDelayChoice: "2h",
};

export default function Home() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playlist, setPlaylist] = useState<PlaylistResult | null>(null);

  const showEndingToggle = form.length === "600_plus";

  const totalLength = useMemo(() => {
    if (!playlist) return null;
    return formatDuration(playlist.totalDurationSeconds);
  }, [playlist]);

  const handleSubmit = async () => {
    try {
      setError(null);
      setLoading(true);
      setPlaylist(null);

      const response = await fetch("/api/playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: form.topic,
          length: form.length,
          sportsMode: form.sportsMode,
          keepEndingHidden: showEndingToggle ? form.keepEndingHidden : false,
          endingDelayChoice: form.keepEndingHidden
            ? form.endingDelayChoice
            : undefined,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Unable to generate playlist.");
      }
      setPlaylist(payload.playlist);
    } catch (err: any) {
      setError(err.message ?? "Something went wrong.");
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
          <p className={styles.kicker}>Lean MVP · Topic → Playlist</p>
          <h1>Intentional YouTube curation in two inputs.</h1>
          <p>
            Drop a topic, set a time budget, toggle spoilers, and get a
            sequenced playlist that feels human.
          </p>
        </header>

        <div className={styles.grid}>
          <section className={styles.formPanel}>
            <form onSubmit={handleFormSubmit}>
              <label className={styles.label}>
                Topic
                <textarea
                  className={styles.textarea}
                  placeholder='e.g. "MH370" or "NBA Lakers 2020 run"'
                  value={form.topic}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, topic: event.target.value }))
                  }
                  rows={3}
                  required
                />
              </label>

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

              {showEndingToggle && (
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
                    <label className={styles.label}>
                      When should the ending drop?
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
                  )}
                </div>
              )}

              <button
                type="submit"
                className={styles.primaryButton}
                disabled={loading}
              >
                {loading ? "Scoring videos…" : "Generate Playlist"}
              </button>

              {error && <p className={styles.error}>{error}</p>}
            </form>
          </section>

          <section className={styles.resultsPanel}>
            {playlist ? (
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
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <p className={styles.cardEyebrow}>Curated Playlist</p>
          <h2>{playlist.playlistTitle}</h2>
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
            Save to YouTube
          </a>
        ) : (
          <span className={styles.note}>
            Add your YouTube OAuth creds to auto-save playlists.
          </span>
        )}

        <button
          type="button"
          onClick={onRegenerate}
          className={styles.ghostButton}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Regenerate with new vibe"}
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
    <div className={styles.empty}>
      <p>Ready when you are. Topic + length is all it takes.</p>
      <ul>
        <li>True crime rabbit holes</li>
        <li>Sports runs without spoilers</li>
        <li>10+ hour mysteries with hidden endings</li>
      </ul>
    </div>
  );
}

function friendlyTag(tag: string) {
  switch (tag) {
    case "intro":
      return "Intro";
    case "context":
      return "Context";
    case "deep_dive":
      return "Main deep dive";
    case "ending":
      return "Ending";
    default:
      return "Related";
  }
}

