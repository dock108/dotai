import { redirect } from "next/navigation";

type Params = {
  params: {
    gameId: string;
  };
};

/**
 * Legacy game detail page - redirects to the comprehensive boxscore detail page.
 * 
 * This route is maintained for backward compatibility with existing links.
 * All game detail views should use /admin/boxscores/[id] which provides
 * a tabbed interface with team stats, player stats, odds, metrics, and actions.
 */
export default async function GameDetailPage({ params }: Params) {
  redirect(`/admin/boxscores/${params.gameId}`);
}

