"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./AdminNav.module.css";

interface NavItem {
  href: string;
  label: string;
  icon: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Data",
    items: [
      { href: "/admin/theory-bets", label: "Dashboard", icon: "📊" },
      { href: "/admin/theory-bets/games", label: "Games", icon: "🏀" },
      { href: "/admin/theory-bets/teams", label: "Teams", icon: "👥" },
    ],
  },
  {
    title: "Ingestion",
    items: [
      { href: "/admin/theory-bets/ingestion", label: "Scraper Runs", icon: "⚙️" },
    ],
  },
];

export function AdminNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/admin/theory-bets") {
      return pathname === "/admin/theory-bets";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoText}>Sports Admin</div>
        <div className={styles.logoSub}>Data Management</div>
      </div>

      <nav className={styles.nav}>
        {navSections.map((section) => (
          <div key={section.title} className={styles.navSection}>
            <div className={styles.navSectionTitle}>{section.title}</div>
            {section.items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navLink} ${isActive(item.href) ? styles.navLinkActive : ""}`}
              >
                <span className={styles.navIcon}>{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className={styles.footer}>
        <Link href="/" className={styles.footerLink}>
          ← Back to Theory Bets
        </Link>
      </div>
    </aside>
  );
}

