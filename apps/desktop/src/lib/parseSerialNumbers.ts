/** Parse one or many serial numbers from bulk entry (newline, comma, or whitespace separated). */
export function parseSerialNumbers(raw: string): string[] {
  const tokens = raw
    .split(/[\n,;]+/)
    .flatMap((line) => line.trim().split(/\s+/))
    .map((token) => token.trim())
    .filter(Boolean);

  const seen = new Set<string>();
  const unique: string[] = [];
  for (const token of tokens) {
    const key = token.toUpperCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(token);
  }
  return unique;
}
