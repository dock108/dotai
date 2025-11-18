"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import styles from "./page.module.css";

interface Lesson {
  id: number;
  number: number;
  title: string;
  skill: string;
  skillDescription: string;
  goal: string;
  scenario: string;
  answerFormat: string;
  maxTurns: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ScoreResponse {
  verdict: string;
  confidence: number;
  reasoning: string;
  guardrail_flags: string[];
}

export default function GamePage() {
  const params = useParams();
  const router = useRouter();
  const lessonId = params.id as string;

  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [turns, setTurns] = useState(0);

  useEffect(() => {
    fetch(`/api/lessons/${lessonId}`)
      .then((res) => res.json())
      .then((data) => {
        setLesson(data);
        setMessages([
          {
            role: "assistant",
            content: `Welcome! ${data.scenario}\n\nGoal: ${data.goal}\n\nAnswer format: ${data.answerFormat}`,
          },
        ]);
      })
      .catch(() => router.push("/"));
  }, [lessonId, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || loading || !lesson) return;

    const userMessage: Message = { role: "user", content: userInput };
    setMessages((prev) => [...prev, userMessage]);
    setUserInput("");
    setLoading(true);
    setTurns((prev) => prev + 1);

    try {
      const response = await fetch("/api/game/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lessonId: parseInt(lessonId),
          userMessage: userInput,
          history: messages,
          scenario: lesson.scenario,
        }),
      });

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reasoning || data.message || "Processing..." },
      ]);

      if (data.verdict) {
        setScore(data);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Could not process your message. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!lesson) {
    return <div className={styles.container}>Loading...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button onClick={() => router.push("/")} className={styles.backButton}>
          ← Back to Lessons
        </button>
        <h1>{lesson.title}</h1>
        <p className={styles.skill}>{lesson.skill}</p>
        <p className={styles.goal}>Goal: {lesson.goal}</p>
        <div className={styles.turns}>
          Turn {turns} / {lesson.maxTurns}
        </div>
      </header>

      <div className={styles.gameArea}>
        <div className={styles.messages}>
          {messages.map((msg, idx) => (
            <div key={idx} className={styles[msg.role]}>
              <div className={styles.messageLabel}>{msg.role === "user" ? "You" : "AI"}</div>
              <div className={styles.messageContent}>{msg.content}</div>
            </div>
          ))}
          {loading && <div className={styles.loading}>AI is thinking...</div>}
        </div>

        <form onSubmit={handleSubmit} className={styles.inputForm}>
          <textarea
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Type your question or answer..."
            className={styles.textarea}
            rows={3}
            disabled={loading || turns >= lesson.maxTurns}
          />
          <button type="submit" disabled={loading || !userInput.trim() || turns >= lesson.maxTurns} className={styles.submitButton}>
            Send
          </button>
        </form>

        {score && (
          <div className={styles.scoreCard}>
            <h3>Score Card</h3>
            <div className={styles.verdict}>
              <strong>Verdict:</strong> {score.verdict}
            </div>
            <div className={styles.confidence}>
              <strong>Confidence:</strong> {(score.confidence * 100).toFixed(0)}%
            </div>
            {score.guardrail_flags.length > 0 && (
              <div className={styles.flags}>
                <strong>Flags:</strong> {score.guardrail_flags.join(", ")}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

