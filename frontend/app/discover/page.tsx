import { WatchlistTable } from "@/components/watchlist/watchlist-table";
import { demoWatchlist } from "@/lib/demo-data";

export default function DiscoverPage() { return <WatchlistTable entries={demoWatchlist} />; }
