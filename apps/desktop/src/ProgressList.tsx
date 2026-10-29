export type ProgressStep = {
  id: string;
  label: string;
  status: "active" | "done";
  detail: string;
};

export function applyProgress(
  steps: ProgressStep[],
  event: { id?: string; label?: string; status?: "active" | "done"; detail?: string },
): ProgressStep[] {
  if (!event.id || !event.label) return steps;
  const row: ProgressStep = {
    id: event.id,
    label: event.label,
    status: event.status === "done" ? "done" : "active",
    detail: event.detail ?? "",
  };
  const index = steps.findIndex((step) => step.id === row.id);
  if (index < 0) return [...steps, row];
  const next = steps.slice();
  next[index] = { ...next[index], ...row, detail: event.detail ?? next[index].detail };
  return next;
}

export function ProgressList({ steps }: { steps: ProgressStep[] }) {
  if (steps.length === 0) return null;
  return (
    <ol className="progress-steps">
      {steps.map((step) => (
        <li key={step.id} data-status={step.status}>
          <strong>{step.status === "done" ? "完成" : "进行中"} · {step.label}</strong>
          {step.detail ? <span>{step.detail}</span> : null}
        </li>
      ))}
    </ol>
  );
}
