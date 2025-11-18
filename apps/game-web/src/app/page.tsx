"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import styles from "./page.module.css";

interface Lesson {
  id: number;
  number: number;
  title: string;
  skill: string;
  skillDescription: string;
  goal: string;
  scenario: string;
}

export default function Home() {
  const router = useRouter();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/lessons")
      .then((res) => res.json())
      .then((data) => {
        setLessons(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.container}>Loading lessons...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>AI Prompting Game</h1>
        <p className={styles.subtitle}>Learn to prompt AI effectively through interactive lessons</p>
      </header>

      <div className={styles.lessonsGrid}>
        {lessons.map((lesson) => (
          <div key={lesson.id} className={styles.lessonCard} onClick={() => router.push(`/game/${lesson.id}`)}>
            <div className={styles.lessonNumber}>Lesson {lesson.number}</div>
            <h2 className={styles.lessonTitle}>{lesson.title}</h2>
            <p className={styles.lessonSkill}>{lesson.skill}</p>
            <p className={styles.lessonDescription}>{lesson.skillDescription}</p>
            <div className={styles.lessonGoal}>
              <strong>Goal:</strong> {lesson.goal}
            </div>
          </div>
        ))}
      </div>

      <div className={styles.promo}>
        <p>
          <strong>Not getting the results you expect?</strong> Try the quick AI prompting game on iOS / web.
        </p>
      </div>
    </div>
  );
}

