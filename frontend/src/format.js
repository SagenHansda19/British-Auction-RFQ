
export function formatTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatDate(isoDate) {
  if (!isoDate) return "-";
  return new Date(isoDate).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatMoney(amount) {
  if (amount == null) return "-";
  return "₹" + Number(amount).toLocaleString("en-IN", { minimumFractionDigits: 2 });
}

export function formatDuration(ms) {
  if (ms <= 0) return "00:00";
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

const TRIGGER_LABELS = {
  ANY_BID: "Bid received in last X minutes",
  ANY_RANK_CHANGE: "Any supplier rank change in last X minutes",
  L1_CHANGE: "Lowest bidder (L1) change in last X minutes",
};

export function triggerLabel(trigger) {
  return TRIGGER_LABELS[trigger] || trigger;
}
