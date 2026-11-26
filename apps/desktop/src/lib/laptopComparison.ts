import type { ComparisonLaptop } from '../services/api/ComparisonService';
import { splitModelNotes } from './modelNotes';

export interface ComparisonSlot {
  id: number;
  laptop: ComparisonLaptop | null;
}

export const MAX_COMPARISON_LAPTOPS = 4;
const DEFAULT_COMPONENTS = [
  'Processor',
  'RAM',
  'Storage',
  'Graphics',
  'Display',
  'Battery',
  'Charging',
  'Physical design',
  'Connectivity',
  'Ports',
  'Camera and audio',
  'Keyboard and security',
  'Operating system and warranty',
];
const CPU_COMPONENTS = [
  'CPU cores',
  'CPU threads',
  'CPU core layout',
  'CPU max turbo',
  'CPU cache',
];

const COMPONENT_ALIASES: [string, RegExp][] = [
  ['CPU cores', /^(?:(?:cpu|processor|total) )?cores?(?: count)?$/i],
  ['CPU threads', /^(?:(?:cpu|processor|total) )?threads?(?: count)?$/i],
  ['CPU core layout', /^(?:(?:cpu|processor) )?core (?:layout|configuration)$/i],
  [
    'CPU max turbo',
    /^(?:(?:cpu|processor) )?(?:max(?:imum)? )?(?:turbo|boost)(?: clock| frequency)?$/i,
  ],
  ['CPU cache', /^(?:(?:cpu|processor) )?cache$/i],
  ['Processor', /^(processor|cpu|chipset|cores|threads|clock|architecture|cache|tdp)\b/i],
  ['RAM', /^(ram|memory|sodimm)\b/i],
  ['Storage', /^(storage|ssd|hdd|nvme|drive)\b/i],
  ['Graphics', /^(graphics|gpu|vram|video memory)\b/i],
  [
    'Display',
    /^(display|screen|panel|refresh|brightness|resolution|colour gamut|color gamut|touchscreen)\b/i,
  ],
  ['Battery', /^battery\b/i],
  ['Charging', /^(charging|charger|power adapter)\b/i],
  ['Physical design', /^(physical design|chassis|dimensions|weight|colo[u]?rs?|build)\b/i],
  ['Connectivity', /^(connectivity|wireless|wi[ -]?fi|bluetooth|network)\b/i],
  ['Ports', /^(ports?|interfaces?|usb|thunderbolt|hdmi)\b/i],
  ['Camera and audio', /^(camera|webcam|audio|speakers?|microphone)\b/i],
  ['Keyboard and security', /^(keyboard|security|fingerprint|touchpad)\b/i],
  ['Operating system and warranty', /^(operating system|os|warranty)\b/i],
];
const PRIVATE_NOTE =
  /^(internal|private|supplier|purchase|cost|margin|staff|vendor|serial|credentials?|password|token|database|api|source)\b/i;

export function initialComparisonSlots(): ComparisonSlot[] {
  return [
    { id: 1, laptop: null },
    { id: 2, laptop: null },
  ];
}

export function addComparisonSlot(slots: ComparisonSlot[], id: number): ComparisonSlot[] {
  return slots.length < MAX_COMPARISON_LAPTOPS ? [...slots, { id, laptop: null }] : slots;
}

export function removeComparisonSlot(slots: ComparisonSlot[], id: number): ComparisonSlot[] {
  return slots.length > 2 && id > 2 ? slots.filter((slot) => slot.id !== id) : slots;
}

export function setComparisonLaptop(
  slots: ComparisonSlot[],
  id: number,
  laptop: ComparisonLaptop | null,
): ComparisonSlot[] {
  return slots.map((slot) => (slot.id === id ? { ...slot, laptop } : slot));
}

function specsByComponent(laptop: ComparisonLaptop | null, customer: boolean) {
  const grouped = new Map<string, { heading: string; values: string[] }>();
  function add(label: string, detail: string) {
    if (!detail.trim() || (customer && PRIVATE_NOTE.test(label))) return;
    const heading = COMPONENT_ALIASES.find(([, pattern]) => pattern.test(label))?.[0] ?? label;
    const key = heading.toLocaleLowerCase();
    const existing = grouped.get(key);
    const value =
      CPU_COMPONENTS.includes(heading) || heading.toLocaleLowerCase() === label.toLocaleLowerCase()
        ? detail
        : label + ': ' + detail;
    if (!existing) grouped.set(key, { heading, values: [value] });
    else if (!existing.values.includes(value)) existing.values.push(value);
  }
  if (!laptop) return grouped;

  laptop.specifications.forEach((item) => add(item.component, item.detail));
  if (laptop.source === 'inventory' && laptop.saved_notes) {
    const { description, specNotes } = splitModelNotes(laptop.saved_notes);
    if (description) add('Description', description);
    const [savedSpecs, ...sourceNotes] = specNotes.split(/\r?\n---\r?\n/);
    let label: string | null = null;
    let lines: string[] = [];
    const unlabelled: string[] = [];
    for (const line of savedSpecs.split(/\r?\n/)) {
      const field = line.match(/^\s*([\p{L}][\p{L}\d .&/()+-]{0,89}):\s*(.+)$/u);
      if (field) {
        if (label) add(label, lines.join('\n'));
        label = field[1];
        lines = [field[2]];
      } else if (label && (!customer || !PRIVATE_NOTE.test(line.trim()))) {
        lines.push(line);
      } else {
        unlabelled.push(line);
      }
    }
    if (label) add(label, lines.join('\n'));
    if (!customer && unlabelled.join('\n').trim()) add('Saved notes', unlabelled.join('\n'));
    if (!customer && sourceNotes.length) add('Saved notes', sourceNotes.join('\n---\n'));
  }
  return grouped;
}

export function comparisonRows(slots: ComparisonSlot[], customer = false) {
  const specs = slots.map(({ laptop }) => specsByComponent(laptop, customer));
  const cpuHeadings = CPU_COMPONENTS.filter((label) =>
    specs.some((grouped) => grouped.has(label.toLocaleLowerCase())),
  );
  const headings = new Map(
    [DEFAULT_COMPONENTS[0], ...cpuHeadings, ...DEFAULT_COMPONENTS.slice(1)].map((label) => [
      label.toLocaleLowerCase(),
      label,
    ]),
  );
  for (const grouped of specs) {
    grouped.forEach(({ heading }, key) => {
      if (!headings.has(key)) headings.set(key, heading);
    });
  }
  return Array.from(headings, ([key, heading]) => {
    const values = specs.map((grouped) => grouped.get(key)?.values ?? []);
    const known = values
      .filter((parts) => parts.length > 0)
      .map((parts) =>
        parts.join('\n').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim(),
      );
    return { key, heading, values, differs: new Set(known).size > 1 };
  });
}
