import { AppTile } from "@dock108/ui";
import styles from "./page.module.css";

/**
 * Application metadata for the landing portal.
 * 
 * Each entry represents a dock108 sub-application accessible from this hub.
 * Keep hrefs in sync with Traefik routing configuration in docker-compose.yml.
 */
const apps = [
  {
    title: "AI Prompt Game",
    description: "Train reactions, guess model outputs, and sharpen instincts.",
    href: "https://game.dock108.ai",
  },
  {
    title: "Highlights",
    description: "Auto-build sports highlight reels with one query.",
    href: "https://highlights.dock108.ai",
  },
  {
    title: "Theory Bets",
    description: "Interpret betting ideas, generate strategy specs, and alerts.",
    href: "https://bets.dock108.ai",
  },
  {
    title: "Stock Interpreter",
    description: "Catalyst-aware equities playbooks with backtest blueprints.",
    href: "https://stocks.dock108.ai",
  },
  {
    title: "Crypto Interpreter",
    description: "Narrative-driven crypto entries, exits, diagnostics, and alerts.",
    href: "https://crypto.dock108.ai",
  },
  {
    title: "Conspiracy Decoder",
    description: "Map claims to evidence, sources, and risk levels instantly.",
    href: "https://conspiracy.dock108.ai",
  },
];

/**
 * Main landing page component for dock108 portal.
 * 
 * Displays a hero section and a grid of application tiles linking to
 * all dock108 sub-applications (game, highlights, bets, stocks, crypto, conspiracy).
 * 
 * Uses AppTile component from @dock108/ui for consistent styling.
 */
export default function HomePage() {
  return (
    <>
      <section className={styles.hero}>
        <p>Dock108 • Theory Engine Lab</p>
        <h1>One home for every Dock108 experiment.</h1>
        <p>Choose a surface to launch. Each runs its own stack, tuned for scale, guardrails, and fast iteration.</p>
      </section>

      <section className={styles.grid}>
        {apps.map((app) => (
          <AppTile key={app.title} {...app} />
        ))}
      </section>
    </>
  );
}

