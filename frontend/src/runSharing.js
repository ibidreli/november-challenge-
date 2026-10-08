export function runUrl() {
  const url = new URL("/", window.location.origin);
  url.searchParams.set("tab", "groups");
  return url.href;
}

export function canShareImage(file) {
  try {
    return Boolean(
      file && navigator.share && navigator.canShare?.({ files: [file] }),
    );
  } catch {
    return false;
  }
}
