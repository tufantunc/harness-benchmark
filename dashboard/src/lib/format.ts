export function pct(n: number): string {
  return (n * 100).toFixed(1) + '%';
}

export function fmt(n: number): string {
  return Math.round(n).toLocaleString();
}

export function secs(n: number): string {
  return Math.round(n) + 's';
}

export function scoreBadge(rate: number): string {
  if (rate >= 0.6) return 'bg-green-500/15 text-green-400 border-green-500/30';
  if (rate >= 0.4) return 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30';
  return 'bg-red-500/15 text-red-400 border-red-500/30';
}
