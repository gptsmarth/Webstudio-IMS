const DESCRIPTION_PREFIX = 'DESCRIPTION:\n';

/** Split stored product model notes into marketing description and structured spec extras. */
export function splitModelNotes(notes: string | null | undefined): {
  description: string;
  specNotes: string;
} {
  if (!notes?.trim()) {
    return { description: '', specNotes: '' };
  }

  if (!notes.startsWith(DESCRIPTION_PREFIX)) {
    return { description: '', specNotes: notes.trim() };
  }

  const afterMarker = notes.slice(DESCRIPTION_PREFIX.length);
  const lines = afterMarker.split('\n');
  const descriptionLines: string[] = [];
  const specLines: string[] = [];
  let inDescription = true;

  for (const line of lines) {
    const trimmed = line.trim();
    if (inDescription) {
      if (/^[A-Za-z][\w\s/&]*:\s+\S/.test(trimmed)) {
        inDescription = false;
        specLines.push(line);
      } else {
        descriptionLines.push(line);
      }
    } else {
      specLines.push(line);
    }
  }

  return {
    description: descriptionLines.join('\n').trim(),
    specNotes: specLines.join('\n').trim(),
  };
}

/** Persist description and structured spec lines in product model notes. */
export function composeModelNotes(description: string, specNotes: string): string | null {
  const desc = description.trim();
  const specs = specNotes.trim();

  if (desc && specs) {
    return `${DESCRIPTION_PREFIX}${desc}\n\n${specs}`;
  }
  if (desc) {
    return `${DESCRIPTION_PREFIX}${desc}`;
  }
  return specs || null;
}
