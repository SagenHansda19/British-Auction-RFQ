import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";

function toLocalInput(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function minutesFromNow(minutes) {
  return toLocalInput(new Date(Date.now() + minutes * 60000));
}

const inputClass = "mt-1 w-full rounded border border-slate-300 px-3 py-2";

export default function CreateRfq({ currentUser }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    reference_id: `RFQ-${Date.now().toString().slice(-6)}`,
    bid_start_at: minutesFromNow(0),
    close_at: minutesFromNow(15),
    forced_close_at: minutesFromNow(30),
    pickup_date: minutesFromNow(7 * 24 * 60).slice(0, 10),
    trigger_window_min: 10,
    extension_min: 5,
    trigger: "ANY_BID",
  });
  const [clientError, setClientError] = useState("");

  const createRfq = useMutation({
    mutationFn: api.createRfq,
    onSuccess: (rfq) => {
      queryClient.invalidateQueries({ queryKey: ["rfqs"] });
      navigate(`/rfqs/${rfq.id}`);
    },
  });

  if (currentUser?.role !== "BUYER") {
    return <p>Only buyers can create RFQs. Switch to a buyer in the top-right corner.</p>;
  }

  function update(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  function submit(e) {
    e.preventDefault();
    if (form.forced_close_at <= form.close_at) {
      setClientError("Forced close time must be later than the bid close time.");
      return;
    }
    setClientError("");
    createRfq.mutate({
      name: form.name,
      reference_id: form.reference_id,
      // local time -> UTC
      bid_start_at: new Date(form.bid_start_at).toISOString(),
      close_at: new Date(form.close_at).toISOString(),
      forced_close_at: new Date(form.forced_close_at).toISOString(),
      pickup_date: form.pickup_date,
      config: {
        trigger_window_min: Number(form.trigger_window_min),
        extension_min: Number(form.extension_min),
        trigger: form.trigger,
      },
    });
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-6 rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-2xl font-semibold">Create RFQ (British Auction)</h1>

      <section className="grid grid-cols-2 gap-4">
        <label className="col-span-2">RFQ name
          <input required value={form.name} onChange={update("name")} className={inputClass}
                 placeholder="Mumbai to Delhi - 20ft container" />
        </label>
        <label>Reference ID
          <input required value={form.reference_id} onChange={update("reference_id")} className={inputClass} />
        </label>
        <label>Pickup / service date
          <input required type="date" value={form.pickup_date} onChange={update("pickup_date")} className={inputClass} />
        </label>
        <label>Bid start
          <input required type="datetime-local" value={form.bid_start_at} onChange={update("bid_start_at")} className={inputClass} />
        </label>
        <label>Bid close
          <input required type="datetime-local" value={form.close_at} onChange={update("close_at")} className={inputClass} />
        </label>
        <label className="col-span-2">Forced bid close (must be later than bid close)
          <input required type="datetime-local" value={form.forced_close_at} onChange={update("forced_close_at")} className={inputClass} />
        </label>
      </section>

      <section className="grid grid-cols-2 gap-4 rounded border border-slate-200 bg-slate-50 p-4">
        <h2 className="col-span-2 font-semibold">British auction configuration</h2>
        <label>Trigger window X (minutes)
          <input required type="number" min="1" value={form.trigger_window_min} onChange={update("trigger_window_min")} className={inputClass} />
        </label>
        <label>Extension duration Y (minutes)
          <input required type="number" min="1" value={form.extension_min} onChange={update("extension_min")} className={inputClass} />
        </label>
        <label className="col-span-2">Extension trigger
          <select value={form.trigger} onChange={update("trigger")} className={inputClass}>
            <option value="ANY_BID">Bid received in last X minutes</option>
            <option value="ANY_RANK_CHANGE">Any supplier rank change in last X minutes</option>
            <option value="L1_CHANGE">Lowest bidder (L1) change in last X minutes</option>
          </select>
        </label>
      </section>

      {(clientError || createRfq.error) && (
        <p className="rounded bg-red-50 p-3 text-sm text-red-700">{clientError || createRfq.error.message}</p>
      )}
      <button disabled={createRfq.isPending} className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50">
        {createRfq.isPending ? "Creating..." : "Create RFQ"}
      </button>
    </form>
  );
}
