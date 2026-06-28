import { Bookmark, Clock, Star } from 'lucide-react';
import { EMPTY_SAVED_REPORTS } from '../../types/savedReports';

export function SavedReportsPlaceholder(): JSX.Element {
  const { saved, favourites, recent } = EMPTY_SAVED_REPORTS;

  return (
    <aside className="report-saved" aria-label="Saved reports (coming soon)">
      <h2 className="report-saved__title">Saved reports</h2>
      <p className="report-saved__hint">Architecture prepared for saved, favourite, and recently used report definitions.</p>
      <ul className="report-saved__list">
        <li className="report-saved__item report-saved__item--disabled">
          <Bookmark size={14} aria-hidden />
          <span>Saved reports ({saved.length})</span>
        </li>
        <li className="report-saved__item report-saved__item--disabled">
          <Star size={14} aria-hidden />
          <span>Favourite reports ({favourites.length})</span>
        </li>
        <li className="report-saved__item report-saved__item--disabled">
          <Clock size={14} aria-hidden />
          <span>Recently used ({recent.length})</span>
        </li>
      </ul>
    </aside>
  );
}
