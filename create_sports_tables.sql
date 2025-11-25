-- Create sports data tables
CREATE TABLE IF NOT EXISTS sports_leagues (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    level VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sports_leagues_code ON sports_leagues(code);

CREATE TABLE IF NOT EXISTS sports_teams (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES sports_leagues(id) ON DELETE CASCADE,
    abbreviation VARCHAR(10),
    full_name VARCHAR(100) NOT NULL,
    city VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sports_teams_league ON sports_teams(league_id);
CREATE INDEX IF NOT EXISTS idx_sports_teams_league_abbr ON sports_teams(league_id, abbreviation);

CREATE TABLE IF NOT EXISTS sports_games (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES sports_leagues(id) ON DELETE CASCADE,
    season INTEGER,
    season_type VARCHAR(50),
    game_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team_id INTEGER REFERENCES sports_teams(id),
    away_team_id INTEGER REFERENCES sports_teams(id),
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(20) DEFAULT 'scheduled',
    scrape_version INTEGER,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_games_league_season_date ON sports_games(league_id, season, game_date);
CREATE INDEX IF NOT EXISTS idx_games_teams ON sports_games(home_team_id, away_team_id);

CREATE TABLE IF NOT EXISTS sports_team_boxscores (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES sports_games(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES sports_teams(id),
    stats JSONB,
    source VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_team_boxscores_game ON sports_team_boxscores(game_id);

CREATE TABLE IF NOT EXISTS sports_player_boxscores (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES sports_games(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES sports_teams(id),
    player_name VARCHAR(200),
    stats JSONB,
    source VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_player_boxscores_game ON sports_player_boxscores(game_id);

CREATE TABLE IF NOT EXISTS sports_game_odds (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES sports_games(id) ON DELETE CASCADE,
    book VARCHAR(50) NOT NULL,
    market_type VARCHAR(50) NOT NULL,
    side VARCHAR(20),
    line NUMERIC,
    price NUMERIC,
    is_closing_line BOOLEAN DEFAULT FALSE,
    observed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sports_odds_identity ON sports_game_odds(game_id, book, market_type, is_closing_line);

CREATE TABLE IF NOT EXISTS sports_scrape_runs (
    id SERIAL PRIMARY KEY,
    scraper_type VARCHAR(50) NOT NULL,
    league_id INTEGER NOT NULL REFERENCES sports_leagues(id) ON DELETE CASCADE,
    season INTEGER,
    season_type VARCHAR(50),
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_by VARCHAR(200),
    job_id VARCHAR(100),
    summary TEXT,
    error_details TEXT,
    config JSONB DEFAULT '{}'::jsonb NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_league_status ON sports_scrape_runs(league_id, status);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_created ON sports_scrape_runs(created_at);

-- Insert default leagues
INSERT INTO sports_leagues (code, name, level) VALUES 
    ('NBA', 'National Basketball Association', 'professional'),
    ('NCAAB', 'NCAA Men''s Basketball', 'college'),
    ('NFL', 'National Football League', 'professional'),
    ('NCAAF', 'NCAA Football', 'college'),
    ('MLB', 'Major League Baseball', 'professional'),
    ('NHL', 'National Hockey League', 'professional')
ON CONFLICT (code) DO NOTHING;

