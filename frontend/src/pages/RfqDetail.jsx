import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import BidForm from "../components/BidForm";
import StatusBadge from "../components/StatusBadge";
import { formatDate, formatDuration, formatMoney, formatTime, triggerLabel } from "../format";
import { useServerNow } from "../useServerNow";

export default function RfqDetail({ currentUser }) {
  const { id } = useParams();
  const { data: rfq, error } = useQuery({
    queryKey: ["rfq", id],
    queryFn: () => api.getRfq(id),
    refetchInterval: 3000,
  });
  const { data: events = [] } = useQuery({
    queryKey: ["events", id],
    queryFn: () => api.getEvents(id),
    refetchInterval: 3000,
  });

  if (error) return <p className="text-red-600">{error.message}</p>;
  if (!rfq) return <p>Loading...</p>;

  const extended = rfq.current_close_at !== rfq.original_close_at;
  const currentBidIds = new Set(rfq.ranking.map((b) => b.id));
  const savings = rfq.starting_price && rfq.lowest_bid ? rfq.starting_price - rfq.lowest_bid : 0;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-sm text-blue-700 hover:underline">← All auctions</Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{rfq.name}</h1>
          <StatusBadge status={rfq.status} />
        </div>
        <p className="text-sm text-slate-500">{rfq.reference_id} · Pickup {formatDate(rfq.pickup_date)}</p>
      </div>

      {extended && (
        <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm">
          Auction extended {rfq.extension_count} time(s): close moved from{" "}
          <strong>{formatTime(rfq.original_close_at)}</strong> to{" "}
          <strong>{formatTime(rfq.current_close_at)}</strong>. It can never go past the forced close
          ({formatTime(rfq.forced_close_at)}).
        </div>
      )}

      {rfq.status === "ACTIVE" && <LivePanel rfq={rfq} />}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card label="Current bid close">{formatTime(rfq.current_close_at)}</Card>
        <Card label="Forced close">{formatTime(rfq.forced_close_at)}</Card>
        <Card label="Bid start">{formatTime(rfq.bid_start_at)}</Card>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <h2 className="mb-2 font-semibold">Auction configuration</h2>
          <p>Trigger window (X): <strong>{rfq.config.trigger_window_min} min</strong></p>
          <p>Extension duration (Y): <strong>{rfq.config.extension_min} min</strong></p>
          <p>Extension trigger: <strong>{triggerLabel(rfq.config.trigger)}</strong></p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <h2 className="mb-2 font-semibold">Auction progress</h2>
          <p>Bids received: <strong>{rfq.bid_count}</strong> · Extensions: <strong>{rfq.extension_count}</strong></p>
          <p>Starting price: <strong>{formatMoney(rfq.starting_price)}</strong></p>
          <p>
            Current lowest: <strong>{formatMoney(rfq.lowest_bid)}</strong>
            {savings > 0 && (
              <span className="text-green-700">
                {" "}(saved {formatMoney(savings)}, {((savings / rfq.starting_price) * 100).toFixed(1)}%)
              </span>
            )}
          </p>
        </div>
      </div>

      {currentUser?.role === "SUPPLIER" && <MyPosition rfq={rfq} supplierId={currentUser.id} />}
      {currentUser?.role === "SUPPLIER" && rfq.status === "ACTIVE" && <BidForm rfqId={id} />}
      {currentUser?.role === "SUPPLIER" && rfq.status !== "ACTIVE" && (
        <p className="text-sm text-slate-500">Bidding is not open for this auction.</p>
      )}

      <BidTable title="Supplier ranking (each supplier's current bid)" bids={rfq.ranking} showRank />
      <BidTable
        title="All bids (sorted by price)"
        bids={rfq.bids}
        note={(bid) => (currentBidIds.has(bid.id) ? "Current" : "Replaced by a lower bid")}
      />

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 font-semibold">Activity log</h2>
        <ul className="space-y-2 text-sm">
          {events.map((event) => (
            <li key={event.id} className="flex gap-3">
              <span className="w-40 shrink-0 text-slate-500">{formatTime(event.created_at)}</span>
              <span className={`w-28 shrink-0 font-semibold ${event.type === "EXTENDED" ? "text-amber-700" : ""}`}>
                {event.type.replace("_", " ")}
              </span>
              <span>
                {event.reason}
                {event.type === "EXTENDED" && (
                  <> — {formatTime(event.old_close_at)} → {formatTime(event.new_close_at)}</>
                )}
              </span>
            </li>
          ))}
          {events.length === 0 && <li className="text-slate-500">No activity yet.</li>}
        </ul>
      </div>
    </div>
  );
}

function LivePanel({ rfq }) {
  const now = useServerNow(rfq.server_time);
  const close = new Date(rfq.current_close_at).getTime();
  const windowStart = close - rfq.config.trigger_window_min * 60000;
  const inWindow = now >= windowStart && now < close;
  const atForcedClose = rfq.current_close_at === rfq.forced_close_at;

  let message;
  if (atForcedClose) {
    message = "Already at the forced close: no more extensions are possible.";
  } else if (inWindow) {
    message = `In the trigger window: "${triggerLabel(rfq.config.trigger)}" now extends the close by ${rfq.config.extension_min} min (never past the forced close).`;
  } else {
    message = `Trigger window opens at ${formatTime(new Date(windowStart).toISOString())} (last ${rfq.config.trigger_window_min} min before close).`;
  }

  return (
    <div className={`flex flex-wrap items-center gap-6 rounded-lg border p-4 ${inWindow ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-white"}`}>
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold text-red-600">
          <span className="h-2 w-2 rounded-full bg-red-600" /> LIVE · ENDS IN
        </div>
        <div className="font-mono text-4xl font-semibold">{formatDuration(close - now)}</div>
      </div>
      <p className={`max-w-xl text-sm ${inWindow ? "text-amber-900" : "text-slate-600"}`}>{message}</p>
    </div>
  );
}

function MyPosition({ rfq, supplierId }) {
  const mine = rfq.ranking.find((b) => b.supplier_id === supplierId);
  const leader = rfq.ranking[0];

  if (!mine) {
    return (
      <p className="rounded border border-slate-200 bg-white p-3 text-sm">
        You haven't bid on this RFQ yet.{leader && <> Current lowest bid (L1): <strong>{formatMoney(leader.total_price)}</strong>.</>}
      </p>
    );
  }
  const gap = mine.total_price - leader.total_price;
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
      <Card label="Your rank">
        <span className="text-2xl">L{mine.rank}</span> <span className="text-slate-500">of {rfq.ranking.length}</span>
      </Card>
      <Card label="Your current bid"><span className="text-2xl">{formatMoney(mine.total_price)}</span></Card>
      <Card label="Lowest bid (L1)">
        <span className="text-2xl">{formatMoney(leader.total_price)}</span>
        <div className={`text-sm ${gap === 0 ? "text-green-700" : "text-slate-500"}`}>
          {gap === 0 ? "You are leading" : `${formatMoney(gap)} above L1`}
        </div>
      </Card>
    </div>
  );
}

function Card({ label, children }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-medium">{children}</div>
    </div>
  );
}

function BidTable({ title, bids, showRank = false, note }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <h2 className="px-4 pt-4 font-semibold">{title}</h2>
      <table className="mt-2 w-full text-left text-sm">
        <thead className="bg-slate-100 text-slate-600">
          <tr>
            {showRank && <th className="px-3 py-2">Rank</th>}
            <th className="px-3 py-2">Supplier</th>
            <th className="px-3 py-2">Carrier</th>
            <th className="px-3 py-2">Freight</th>
            <th className="px-3 py-2">Origin</th>
            <th className="px-3 py-2">Destination</th>
            <th className="px-3 py-2">Total</th>
            <th className="px-3 py-2">Transit</th>
            <th className="px-3 py-2">Valid until</th>
            <th className="px-3 py-2">Bid time</th>
            {note && <th className="px-3 py-2"></th>}
          </tr>
        </thead>
        <tbody>
          {bids.map((bid) => (
            <tr key={bid.id} className={`border-t border-slate-100 ${showRank && bid.rank === 1 ? "bg-green-50" : ""}`}>
              {showRank && <td className="px-3 py-2 font-semibold">L{bid.rank}</td>}
              <td className="px-3 py-2">{bid.supplier_name}</td>
              <td className="px-3 py-2">{bid.carrier_name}</td>
              <td className="px-3 py-2">{formatMoney(bid.freight_charge)}</td>
              <td className="px-3 py-2">{formatMoney(bid.origin_charge)}</td>
              <td className="px-3 py-2">{formatMoney(bid.destination_charge)}</td>
              <td className="px-3 py-2 font-semibold">{formatMoney(bid.total_price)}</td>
              <td className="px-3 py-2">{bid.transit_time_days} days</td>
              <td className="px-3 py-2">{formatDate(bid.quote_valid_until)}</td>
              <td className="px-3 py-2">{formatTime(bid.created_at)}</td>
              {note && <td className="px-3 py-2 text-xs text-slate-500">{note(bid)}</td>}
            </tr>
          ))}
          {bids.length === 0 && (
            <tr>
              <td colSpan="11" className="px-3 py-4 text-center text-slate-500">No bids yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
