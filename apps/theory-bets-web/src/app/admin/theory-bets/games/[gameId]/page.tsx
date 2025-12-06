type Params = {
  params: {
    gameId: string;
  };
};

/**
 * Game detail placeholder.
 * Renders the game id so links resolve instead of redirecting to a missing route.
 */
export default function GameDetailPage({ params }: Params) {
  return (
    <div style={{ padding: "1.5rem" }}>
      <h1>Game {params.gameId}</h1>
      <p>This game detail view is not yet implemented. Game ID: {params.gameId}</p>
    </div>
  );
}

