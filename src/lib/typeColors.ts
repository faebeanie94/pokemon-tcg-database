export const TYPE_COLORS: Record<string, string> = {
  Grass: "bg-green-100 text-green-800 border-green-300",
  Fire: "bg-orange-100 text-orange-800 border-orange-300",
  Water: "bg-sky-100 text-sky-800 border-sky-300",
  Lightning: "bg-yellow-100 text-yellow-800 border-yellow-300",
  Psychic: "bg-purple-100 text-purple-800 border-purple-300",
  Fighting: "bg-red-100 text-red-800 border-red-300",
  Darkness: "bg-slate-200 text-slate-800 border-slate-400",
  Metal: "bg-zinc-100 text-zinc-800 border-zinc-300",
  Dragon: "bg-amber-100 text-amber-900 border-amber-400",
  Fairy: "bg-pink-100 text-pink-800 border-pink-300",
  Colorless: "bg-neutral-100 text-neutral-800 border-neutral-300",
};

export function typeColor(type: string): string {
  return TYPE_COLORS[type] ?? "bg-neutral-100 text-neutral-800 border-neutral-300";
}
