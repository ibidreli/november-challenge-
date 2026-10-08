import { useEffect, useRef, useState } from "react";
import { api, errorText } from "./api";

// Keep already visible data during refresh and load each tab independently.
export default function usePublicResource(path, version, enabled = true) {
  const [state, setState] = useState({ data: null, error: "" });
  const loadedVersion = useRef();
  useEffect(() => {
    if (!enabled || loadedVersion.current === version) return;
    let alive = true;
    setState((previous) => ({ ...previous, error: "" }));
    api(path).then(
      (data) => {
        if (!alive) return;
        loadedVersion.current = version;
        setState({ data, error: "" });
      },
      (error) => {
        if (alive)
          setState((previous) => ({ ...previous, error: errorText(error) }));
      },
    );
    return () => {
      alive = false;
    };
  }, [path, version, enabled]);
  return state;
}
