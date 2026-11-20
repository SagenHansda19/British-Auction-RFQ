import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import StatusBadge from "../components/StatusBadge";
import { formatMoney, formatTime } from "../format";

export default function RfqList() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["rfqs", status],
    queryFn: () => api.getRfqs(status),
    refetchInterval: 3000,
  });
  const text = search.trim().toLowerCase();
  const rfqs = data.filter(
    (r) => r.name.toLowerCase().includes(text) || r.reference_id.toLowerCase().includes(text),
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">British Auctions</h1>
        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or reference ID"
            className="w-64 rounded border border-slate-300 bg-white px-3 py-1"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded border border-slate-300 bg-white px-2 py-1"
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="CLOSED">Closed</option>
            <option value="FORCE_CLOSED">Force Closed</option>
          </select>
        </div>
      </div>

      {error && <p className="text-red-600">{error.message}</p>}
      {isLoading && <p>Loading...</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="px-4 py-2">RFQ</th>
              <th className="px-4 py-2">Current lowest bid</th>
              <th className="px-4 py-2">Current bid close</th>
              <th className="px-4 py-2">Forced close</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Bids</th>
            </tr>
          </thead>
          <tbody>
            {rfqs.map((rfq) => (
              <tr key={rfq.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2">
                  <Link to={`/rfqs/${rfq.id}`} className="font-medium text-blue-700 hover:underline">
                    {rfq.name}
                  </Link>
                  <div className="text-xs text-slate-500">{rfq.reference_id}</div>
                </td>
                <td className="px-4 py-2 font-medium">{formatMoney(rfq.lowest_bid)}</td>
                <td className="px-4 py-2">
                  {formatTime(rfq.current_close_at)}
                  {rfq.current_close_at !== rfq.original_close_at && (
                    <span className="ml-1 text-xs text-amber-700">(extended)</span>
                  )}
                </td>
                <td className="px-4 py-2">{formatTime(rfq.forced_close_at)}</td>
                <td className="px-4 py-2"><StatusBadge status={rfq.status} /></td>
                <td className="px-4 py-2">{rfq.bid_count}</td>
              </tr>
            ))}
            {!isLoading && rfqs.length === 0 && (
              <tr>
                <td colSpan="6" className="px-4 py-6 text-center text-slate-500">
                  {data.length === 0 ? "No auctions yet. Act as a buyer and create one." : "No auctions match your search."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
