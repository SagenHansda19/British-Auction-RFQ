const COLORS = {
  SCHEDULED: "bg-sky-100 text-sky-800",
  ACTIVE: "bg-green-100 text-green-800",
  CLOSED: "bg-slate-200 text-slate-700",
  FORCE_CLOSED: "bg-red-100 text-red-800",
};

const LABELS = {
  SCHEDULED: "Scheduled",
  ACTIVE: "Active",
  CLOSED: "Closed",
  FORCE_CLOSED: "Force Closed",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${COLORS[status]}`}>
      {LABELS[status]}
    </span>
  );
}
