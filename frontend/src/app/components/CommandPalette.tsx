import type { Dispatch, RefObject, SetStateAction } from "react";
import { Search } from "lucide-react";

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  action: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  query: string;
  activeIndex: number;
  commands: CommandItem[];
  inputRef: RefObject<HTMLInputElement | null>;
  setQuery: (value: string) => void;
  setActiveIndex: Dispatch<SetStateAction<number>>;
  onClose: () => void;
}

export function CommandPalette(props: CommandPaletteProps) {
  if (!props.open) return null;

  return (
    <div className="command-overlay" role="dialog" aria-modal="true" aria-label="Command palette">
      <button type="button" className="command-backdrop" onClick={props.onClose} />
      <div className="command-panel">
        <div className="command-input-row">
          <Search size={15} />
          <input
            ref={props.inputRef}
            value={props.query}
            onChange={(event) => props.setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                const command = props.commands[props.activeIndex] ?? props.commands[0];
                command?.action();
                return;
              }

              if (event.key === "ArrowDown") {
                event.preventDefault();
                props.setActiveIndex((current) =>
                  props.commands.length ? (current + 1) % props.commands.length : 0
                );
                return;
              }

              if (event.key === "ArrowUp") {
                event.preventDefault();
                props.setActiveIndex((current) =>
                  props.commands.length
                    ? (current - 1 + props.commands.length) % props.commands.length
                    : 0
                );
                return;
              }

              if (event.key === "Escape") {
                event.preventDefault();
                props.onClose();
              }
            }}
            placeholder="Search commands, pages, and actions..."
          />
        </div>

        <div className="command-list" role="listbox" aria-activedescendant={props.commands[props.activeIndex]?.id}>
          {props.commands.length ? (
            props.commands.map((command, index) => (
              <button
                type="button"
                key={command.id}
                id={command.id}
                role="option"
                aria-selected={index === props.activeIndex}
                className={`command-item ${index === props.activeIndex ? "active" : ""}`}
                onMouseEnter={() => props.setActiveIndex(index)}
                onClick={command.action}
              >
                <span>{command.label}</span>
                <span>{command.hint ?? "Action"}</span>
              </button>
            ))
          ) : (
            <p className="command-empty">No matching commands.</p>
          )}
        </div>
      </div>
    </div>
  );
}
