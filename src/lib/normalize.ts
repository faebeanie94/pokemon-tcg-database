/**
 * Normalization used to match what a grader types (or reads off a card)
 * against catalog rows.
 *
 * Every source spells things slightly differently: card numbers are padded
 * inconsistently ("1" in Base Set, "001" in Japanese sets), names carry
 * accents ("Pokémon"), punctuation ("Mr. Mime", "Farfetch'd") and full-width
 * characters in Japanese printings. Both the stored value and the incoming
 * query go through the same function here, so the comparison is apples to
 * apples. If you change a rule, the catalog must be re-imported — the
 * normalized forms are stored in the database.
 */

/**
 * Runs of Latin letters together with any combining marks on them. Accent
 * folding is confined to these runs, because Unicode also classes the
 * Japanese voiced-sound and long-vowel marks as diacritics: folding them
 * globally turns リザードン (Charizard) into リサトン and makes genuinely
 * different Japanese names compare equal.
 */
const LATIN_RUN = /[\p{Script=Latin}\p{Mn}\p{Me}]+/gu;

/**
 * Collapses a card or set name to a comparison key: NFKC-folded, lowercased,
 * Latin accents removed, and everything that is not a letter or digit dropped.
 *
 * "Mr. Mime" and "mr mime" both become "mrmime"; "Pokémon" becomes "pokemon".
 * CJK characters are letters as far as Unicode is concerned, so Japanese and
 * Chinese names survive intact.
 */
export function normalizeName(input: string | null | undefined): string {
  if (!input) return "";
  return input
    .normalize("NFKC")
    .toLowerCase()
    .replace(LATIN_RUN, (run) => run.normalize("NFD").replace(/\p{Diacritic}/gu, ""))
    .replace(/[^\p{L}\p{N}]/gu, "");
}

/**
 * Collapses a card number so that padded and unpadded printings compare equal.
 *
 * Digit runs lose their leading zeros ("001" -> "1", "TG01" -> "tg1") while
 * letter prefixes and suffixes are kept, because they distinguish real cards
 * ("H1" and "1" are different cards in the same set).
 */
export function normalizeNumber(input: string | null | undefined): string {
  if (!input) return "";
  return input
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]/gu, "")
    .replace(/\d+/g, (digits) => String(Number(digits)));
}

/**
 * Normalizes a set abbreviation ("BS", "sv1a") for comparison.
 */
export function normalizeSetToken(input: string | null | undefined): string {
  return normalizeName(input);
}

/**
 * Sports card numbers like "SSL-SM" keep hyphens as significant separators.
 * Collapse case and other punctuation, then strip leading zeros from digit runs.
 */
export function normalizeSportsNumber(input: string | null | undefined): string {
  if (!input) return "";
  return input
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}-]/gu, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .replace(/\d+/g, (digits) => String(Number(digits)));
}

/**
 * Fold a parallel label ("HALO REF.", "Ruby Ref") for comparison / card_uid.
 */
export function normalizeParallel(input: string | null | undefined): string {
  return normalizeName(input);
}
