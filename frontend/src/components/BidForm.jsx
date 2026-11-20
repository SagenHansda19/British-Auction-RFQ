import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { formatMoney, formatTime } from "../format";

const inputClass = "mt-1 w-full rounded border border-slate-300 px-3 py-2";

export default function BidForm({ rfqId }) {
  const queryClient = useQueryClient();
  const in30Days = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const [form, setForm] = useState({
    carrier_name: "",
    freight_charge: "",
    origin_charge: "",
    destination_charge: "",
    transit_time_days: 3,
    quote_valid_until: in30Days,
  });

  const placeBid = useMutation({
    mutationFn: (body) => api.placeBid(rfqId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rfq", rfqId] });
      queryClient.invalidateQueries({ queryKey: ["events", rfqId] });
      queryClient.invalidateQueries({ queryKey: ["rfqs"] });
    },
  });

  function update(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  const total = [form.freight_charge, form.origin_charge, form.destination_charge]
    .reduce((sum, value) => sum + (Number(value) || 0), 0);

  function submit(e) {
    e.preventDefault();
    placeBid.mutate({ ...form, transit_time_days: Number(form.transit_time_days) });
  }

  const result = placeBid.data;
  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h2 className="font-semibold">Submit a quote</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <label className="md:col-span-3">Carrier name
          <input required value={form.carrier_name} onChange={update("carrier_name")} className={inputClass} />
        </label>
        <label>Freight charges
          <input required type="number" min="0" step="0.01" value={form.freight_charge} onChange={update("freight_charge")} className={inputClass} />
        </label>
        <label>Origin charges
          <input required type="number" min="0" step="0.01" value={form.origin_charge} onChange={update("origin_charge")} className={inputClass} />
        </label>
        <label>Destination charges
          <input required type="number" min="0" step="0.01" value={form.destination_charge} onChange={update("destination_charge")} className={inputClass} />
        </label>
        <label>Transit time (days)
          <input required type="number" min="0" value={form.transit_time_days} onChange={update("transit_time_days")} className={inputClass} />
        </label>
        <label>Quote valid until
          <input required type="date" value={form.quote_valid_until} onChange={update("quote_valid_until")} className={inputClass} />
        </label>
      </div>
      <div className="flex items-center gap-4">
        <button disabled={placeBid.isPending} className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {placeBid.isPending ? "Submitting..." : "Submit bid"}
        </button>
        <span>Total: <strong>{formatMoney(total)}</strong></span>
      </div>

      {placeBid.error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{placeBid.error.message}</p>}
      {result && (
        <p className="rounded bg-green-50 p-2 text-sm text-green-800">
          Bid of {formatMoney(result.bid.total_price)} placed. You are now <strong>L{result.bid.rank}</strong>.{" "}
          {result.extended
            ? `Your bid extended the auction to ${formatTime(result.current_close_at)}.`
            : "The close time did not change."}
        </p>
      )}
    </form>
  );
}
