import { Trash2, X } from "lucide-react";

type FavoriteType = "company" | "filing" | "headline";

interface FavoriteItem {
  id: string;
  type: FavoriteType;
  symbol?: string;
  title: string;
  subtitle?: string;
  url?: string;
  createdAt: string;
}

interface FavoritesPanelProps {
  open: boolean;
  filter: "all" | FavoriteType;
  favorites: FavoriteItem[];
  onClose: () => void;
  onFilterChange: (value: "all" | FavoriteType) => void;
  onOpenFavorite: (favorite: FavoriteItem) => void;
  onRemoveFavorite: (id: string) => void;
}

export function FavoritesPanel(props: FavoritesPanelProps) {
  if (!props.open) return null;

  return (
    <div className="favorites-overlay" role="dialog" aria-modal="true" aria-label="Favorites panel">
      <button
        type="button"
        className="favorites-backdrop"
        onClick={props.onClose}
      />

      <aside className="favorites-panel">
        <div className="notification-panel-head">
          <div>
            <p className="results-title">Saved Items</p>
            <h3>Favorites</h3>
          </div>
          <button
            type="button"
            className="notification-close"
            onClick={props.onClose}
            aria-label="Close favorites panel"
          >
            <X size={16} />
          </button>
        </div>

        <div className="notification-panel-actions">
          <select
            className="type-select"
            value={props.filter}
            onChange={(event) => props.onFilterChange(event.target.value as "all" | FavoriteType)}
          >
            <option value="all">All favorites</option>
            <option value="company">Company</option>
            <option value="filing">Filing</option>
            <option value="headline">Headline</option>
          </select>
        </div>

        <div className="notification-list">
          {props.favorites.length ? (
            props.favorites.map((favorite) => (
              <article key={favorite.id} className="notification-item unread">
                <div className="notification-item-head">
                  <span className={`chip favorite-${favorite.type}`}>{favorite.type}</span>
                  <span className="chip">{new Date(favorite.createdAt).toLocaleDateString()}</span>
                </div>

                <h4>{favorite.title}</h4>
                {favorite.subtitle ? <p>{favorite.subtitle}</p> : null}
                {favorite.symbol ? <small>Symbol: {favorite.symbol}</small> : null}

                <div className="notification-item-actions">
                  <button
                    type="button"
                    className="secondary-btn mini-btn"
                    onClick={() => props.onOpenFavorite(favorite)}
                  >
                    Open
                  </button>
                  <button
                    type="button"
                    className="secondary-btn mini-btn"
                    onClick={() => props.onRemoveFavorite(favorite.id)}
                  >
                    <Trash2 size={13} />
                    Remove
                  </button>
                </div>
              </article>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No favorites saved yet.</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
