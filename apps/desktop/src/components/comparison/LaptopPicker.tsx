import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { parseApiError } from '../../lib/apiError';
import { ComparisonService, type ComparisonLaptop } from '../../services/api/ComparisonService';

type Mode = 'inventory' | 'external';
const RESEARCH_UNAVAILABLE =
  "Sorry, we couldn't retrieve reliable specifications for this exact laptop model. Please verify the complete model number and try again.";

interface LaptopPickerProps {
  index: number;
  laptop: ComparisonLaptop | null;
  onSelect: (laptop: ComparisonLaptop | null) => void;
}

export function LaptopPicker({ index, laptop, onSelect }: LaptopPickerProps): JSX.Element {
  const [mode, setMode] = useState<Mode>(laptop?.source ?? 'inventory');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [searchOpen, setSearchOpen] = useState(false);
  const [results, setResults] = useState<Awaited<ReturnType<typeof ComparisonService.inventory>>>();
  const [searchError, setSearchError] = useState('');
  const [searching, setSearching] = useState(false);
  const [brand, setBrand] = useState(laptop?.source === 'external' ? laptop.brand : '');
  const [model, setModel] = useState(laptop?.source === 'external' ? laptop.model_number : '');
  const [researching, setResearching] = useState(false);
  const [researchError, setResearchError] = useState('');
  const researchSequence = useRef(0);

  useEffect(
    () => () => {
      researchSequence.current += 1;
    },
    [],
  );

  useEffect(() => {
    if (mode !== 'inventory' || !searchOpen) return;
    let current = true;
    const timer = window.setTimeout(() => {
      void ComparisonService.inventory(search.trim(), page).then(
        (response) => {
          if (!current) return;
          setResults(response);
          setSearching(false);
        },
        (err: unknown) => {
          if (!current) return;
          setSearchError(parseApiError(err, 'Unable to search inventory.'));
          setSearching(false);
        },
      );
    }, 200);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [mode, searchOpen, search, page]);

  function startSearch(nextPage: number) {
    setSearchError('');
    setResults(undefined);
    setSearching(true);
    setPage(nextPage);
    setSearchOpen(true);
  }

  function chooseMode(next: Mode) {
    if (mode === next) return;
    researchSequence.current += 1;
    setMode(next);
    setSearchOpen(false);
    setResearching(false);
    setResearchError('');
  }

  async function research(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!brand.trim() || !model.trim() || researching) return;
    const sequence = ++researchSequence.current;
    setResearchError('');
    setResearching(true);
    try {
      const result = await ComparisonService.research(brand.trim(), model.trim());
      if (sequence === researchSequence.current) onSelect(result);
    } catch {
      if (sequence === researchSequence.current) setResearchError(RESEARCH_UNAVAILABLE);
    } finally {
      if (sequence === researchSequence.current) setResearching(false);
    }
  }

  return (
    <div className="comparison-picker">
      <div className="comparison-picker__modes" aria-label={'Source for laptop ' + index}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          aria-pressed={mode === 'inventory'}
          onClick={() => chooseMode('inventory')}
        >
          From Inventory
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          aria-pressed={mode === 'external'}
          onClick={() => chooseMode('external')}
        >
          Outside Inventory
        </button>
      </div>
      {mode === 'inventory' ? (
        <>
          <label className="comparison-picker__search">
            <Search size={16} aria-hidden />
            <input
              type="search"
              className="input"
              value={search}
              maxLength={160}
              placeholder="Brand, name or model number"
              aria-label={'Search inventory for laptop ' + index}
              onFocus={() => {
                if (!searchOpen) startSearch(1);
              }}
              onChange={(event) => {
                setSearch(event.target.value);
                startSearch(1);
              }}
              onKeyDown={(event) => {
                if (event.key === 'Escape') setSearchOpen(false);
              }}
            />
          </label>
          {searchOpen && (
            <div className="comparison-picker__results">
              {searching && <p role="status">Searching inventory…</p>}
              {searchError && <p role="alert">{searchError}</p>}
              {results?.data.length === 0 && <p role="status">No matching laptops in stock.</p>}
              {!!results?.data.length && (
                <ul aria-label="Matching laptops">
                  {results.data.map((item) => (
                    <li key={item.model_id}>
                      <button
                        type="button"
                        onClick={() => {
                          onSelect(item);
                          setSearch('');
                          setSearchOpen(false);
                        }}
                      >
                        <strong>
                          {item.brand} {item.model_number}
                        </strong>
                        {item.model_name && <span>{item.model_name}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {(results?.meta?.has_previous || results?.meta?.has_next) && (
                <div className="comparison-picker__pagination">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    aria-label="Previous results"
                    disabled={!results?.meta?.has_previous}
                    onClick={() => startSearch(page - 1)}
                  >
                    <ChevronLeft size={16} aria-hidden />
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    aria-label="Next results"
                    disabled={!results?.meta?.has_next}
                    onClick={() => startSearch(page + 1)}
                  >
                    <ChevronRight size={16} aria-hidden />
                  </button>
                </div>
              )}
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setSearchOpen(false)}
              >
                Close results
              </button>
            </div>
          )}
        </>
      ) : (
        <form className="comparison-picker__external" onSubmit={(event) => void research(event)}>
          <label>
            <span className="form-label">Manufacturer / Brand</span>
            <input
              className="input"
              value={brand}
              required
              disabled={researching}
              maxLength={80}
              onChange={(event) => setBrand(event.target.value)}
            />
          </label>
          <label>
            <span className="form-label">Complete model number</span>
            <input
              className="input"
              value={model}
              required
              disabled={researching}
              maxLength={160}
              onChange={(event) => setModel(event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="btn btn-secondary btn-sm"
            disabled={!brand.trim() || !model.trim() || researching}
          >
            {researching ? 'Researching…' : researchError ? 'Retry' : 'Find specifications'}
          </button>
          {researching && (
            <p className="comparison-picker__status" role="status">
              Checking the exact model and variant…
            </p>
          )}
          {researchError && (
            <p className="comparison-picker__status" role="alert">
              {researchError}
            </p>
          )}
        </form>
      )}
      {laptop && (
        <button
          type="button"
          className="btn btn-ghost btn-sm comparison-picker__clear"
          onClick={() => onSelect(null)}
        >
          Clear selection
        </button>
      )}
    </div>
  );
}
