import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

export function usePersistentState<T>(
  key: string,
  getInitialValue: () => T
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(getInitialValue);

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}
