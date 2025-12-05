"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./AdminNav.module.css";

interface NavItem {
  href: string;
  label: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Sports",
    items: [
      { href: "/admin/theory-bets/browser", label: "Data Browser" },
      { href: "/admin/theory-bets/requests", label: "Theory Requests" },
      { href: "/admin/theory-bets/runs", label: "Theory Runs" },
      { href: "/admin/theory-bets/ingestion", label: "Scraper Runs" },
      { href: "/admin/theory-bets/eda", label: "EDA / Modeling Lab" },
    ],
  },
  {
    title: "Crypto",
    items: [
      { href: "/admin/theory-crypto", label: "Dashboard" },
      { href: "/admin/theory-crypto/ingestion", label: "Ingestion Runs" },
      { href: "/admin/theory-crypto/assets", label: "Assets" },
    ],
  },
  {
    title: "Stocks",
    items: [
      { href: "/admin/theory-stocks", label: "Dashboard" },
      { href: "/admin/theory-stocks/ingestion", label: "Ingestion Runs" },
      { href: "/admin/theory-stocks/assets", label: "Assets" },
    ],
  },
];

export function AdminNav() {
  const pathname = usePathname();

  const isActive = (href: string) => pathname.startsWith(href);

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
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className={styles.footer}>
        <Link href="/" className={styles.footerLink}>
          Back to Theory Bets
        </Link>
      </div>
    </aside>
  );
}

