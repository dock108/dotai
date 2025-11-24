"use client";

import { useState } from "react";
import { TheoryForm, PlaylistCard, type PlaylistResult } from "@dock108/ui-kit";
import styles from "./page.module.css";
import type { LengthBucket, EndingDelayChoice } from "@/lib/types";
import { FEATURE_FLAGS } from "@/lib/constants";

/**
 * Length bucket options for playlist generation.
 * 
 * Each bucket represents a target duration range that the backend
 * will use to curate an appropriate number of videos.
 */
const LENGTH_OPTIONS: { value: LengthBucket; label: string }[] = [
  { value: "5_15", label: "5–15 min" },
  { value: "15_30", label: "15–30 min" },
  { value: "30_60", label: "30–60 min" },
  { value: "60_180", label: "1–3 hours" },
  { value: "180_600", label: "3–10 hours" },
  { value: "600_plus", label: "10+ hours" },
];

/**
 * Ending delay choices for long-form playlists (10+ hours).
 * 
 * When "keep ending hidden" is enabled, these options control when
 * spoiler content (e.g., final outcomes, major reveals) first appears.
 */
const ENDING_CHOICES: { value: EndingDelayChoice; label: string }[] = [
  { value: "1h", label: "Reveal after 1 hour" },
  { value: "2h", label: "Reveal after 2 hours" },
  { value: "3h", label: "Reveal after 3 hours" },
  { value: "5h", label: "Reveal after 5 hours" },
  { value: "surprise", label: "Surprise me (60–120 min)" },
];

/**
 * Main page component for AI-curated playlist generation.
 * 
 * Provides a query builder interface where users can:
 * - Enter a topic (e.g., "Lufthansa Heist but not Goodfellas")
 * - Select target length (5 min to 10+ hours)
 * - Enable sports mode (hide spoilers)
 * - Configure ending delay for long-form playlists
 * 
 * On submission, calls POST /api/playlist which forwards to
 * theory-engine-api for actual playlist curation.
 */
export default function Home() {
  const [playlist, setPlaylist] = useState<PlaylistResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (text: string, extraFields?: Record<string, any>) => {
    try {
      setError(null);
      setLoading(true);
      setPlaylist(null);

      const response = await fetch("/api/playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: text,
          length: FEATURE_FLAGS.LONG_FORM_ONLY ? "600_plus" : (extraFields?.length || "30_60"),
          sportsMode: FEATURE_FLAGS.SPORTS_MODE ? (extraFields?.sportsMode === "true" || extraFields?.sportsMode === true) : false,
          keepEndingHidden:
            FEATURE_FLAGS.LONG_FORM_ONLY || extraFields?.length === "600_plus"
              ? (extraFields?.keepEndingHidden === "true" || extraFields?.keepEndingHidden === true)
              : false,
          endingDelayChoice: extraFields?.keepEndingHidden
            ? (extraFields?.endingDelayChoice as EndingDelayChoice)
            : undefined,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Unable to generate playlist.");
      }
      setPlaylist(payload.playlist);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const regenerate = () => {
    if (playlist) {
      handleSubmit(playlist.canonicalTopic, {
        length: playlist.metadata.requestedBucket,
        sportsMode: playlist.metadata.sportsMode,
        keepEndingHidden: playlist.metadata.keepEndingHidden,
        endingDelayChoice: playlist.metadata.endingDelayChoice,
      });
    }
  };

  const extraFields = (
    <div className={styles.extraFields}>
      {FEATURE_FLAGS.LENGTH_SELECTOR && (
        <label className={styles.fieldLabel}>
          Length Target
          <select className={styles.fieldInput} name="length" defaultValue="30_60">
            {LENGTH_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      )}

      {FEATURE_FLAGS.SPORTS_MODE && (
        <label className={styles.toggleLabel}>
          <input type="checkbox" name="sportsMode" className={styles.toggleInput} />
          <span>Sports Mode → hide spoilers</span>
        </label>
      )}

      {(FEATURE_FLAGS.LONG_FORM_ONLY || true) && (
        <>
          <label className={styles.toggleLabel}>
            <input type="checkbox" name="keepEndingHidden" className={styles.toggleInput} />
            <span>Keep the ending hidden</span>
          </label>

          <label className={styles.fieldLabel}>
            When should the outcome first be revealed?
            <select className={styles.fieldInput} name="endingDelayChoice" defaultValue="2h">
              {ENDING_CHOICES.map((choice) => (
                <option key={choice.value} value={choice.value}>
                  {choice.label}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
    </div>
  );

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
            <TheoryForm
              domain="playlist"
              placeholder={
                FEATURE_FLAGS.LONG_FORM_ONLY
                  ? 'e.g. "Lufthansa Heist but not Goodfellas" or "History of Bitcoin, exclude price speculation"'
                  : 'e.g. "Give me YouTube videos about Titanic but never mentioning the movie, more like the ship design and the class stuff."'
              }
              examples={[
                "Titanic but not the movie - ship design and class structure",
                "MH370 disappearance theories",
                "Chernobyl disaster deep dive",
              ]}
              onSubmit={handleSubmit}
              extraFields={extraFields}
              loading={loading}
            />
            {error && <div className={styles.error}>{error}</div>}
          </section>

          <section className={styles.resultsPanel}>
            {playlist ? (
              <PlaylistCard playlist={playlist} onRegenerate={regenerate} loading={loading} />
            ) : (
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
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
