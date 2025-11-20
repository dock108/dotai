/**
 * TypeScript types matching py-core Pydantic schemas.
 * These should stay in sync with packages/py-core/py_core/schemas/theory.py
 */

export type Domain = "bets" | "crypto" | "stocks" | "conspiracies" | "playlist";

export interface TheoryRequest {
  text: string;
  domain?: Domain | null;
  user_tier?: string | null;
}

export interface DataSource {
  name: string;
  cache_status: "cached" | "fresh";
  details?: string | null;
}

export interface TheoryResponse {
  summary: string;
  verdict: string;
  confidence: number; // 0-1
  data_used: DataSource[];
  how_we_got_conclusion: string[];
  long_term_outcome_example: string;
  limitations: string[];
  guardrail_flags: string[];
  model_version?: string | null;
  evaluation_date?: string | null;
}

// Domain-specific request types
export interface BetsRequest extends TheoryRequest {
  sport?: string | null;
  league?: string | null;
  horizon?: string | null; // "single_game" | "full_season"
}

// Domain-specific response types
export interface BetsResponse extends TheoryResponse {
  likelihood_grade: string; // A-F
  edge_estimate?: number | null;
  kelly_sizing_example: string;
}

export interface CryptoResponse extends TheoryResponse {
  pattern_frequency: number; // 0-1
  failure_periods: string[];
  remaining_edge?: number | null;
}

export interface StocksResponse extends TheoryResponse {
  correlation_grade: string;
  fundamentals_match: boolean;
  volume_analysis: string;
}

export interface ConspiraciesResponse extends TheoryResponse {
  likelihood_rating: number; // 0-100
  evidence_for: string[];
  evidence_against: string[];
  historical_parallels: string[];
  missing_data: string[];
}

// API Error types
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

export class NetworkError extends Error {
  constructor(message: string, public originalError?: unknown) {
    super(message);
    this.name = "NetworkError";
  }
}

