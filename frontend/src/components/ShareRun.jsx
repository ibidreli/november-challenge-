import React, { useEffect, useState } from "react";
import Modal from "./Modal";
import { canShareImage, runUrl } from "../runSharing";
import { runDate, pace } from "../time";

export default function ShareRun({ run, onClose }) {
  const url = runUrl();
  const [image, setImage] = useState(null),
    [error, setError] = useState("");
  const [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    import("../shareCard")
      .then(({ createRunCard }) => createRunCard(run, url, controller.signal))
      .then((result) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(result.file);
        setImage({ ...result, src: objectUrl });
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError(
            "Das Bild konnte nicht erstellt werden. Bitte erneut versuchen.",
          );
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [run, url]);
  function download() {
    const link = document.createElement("a");
    link.href = image.src;
    link.download = image.file.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setStatus("Das Bild wird heruntergeladen.");
  }
  async function share() {
    setBusy(true);
    setStatus("");
    try {
      // The image is prepared before this click, preserving browser user activation.
      if (canShareImage(image.file)) {
        await navigator.share({
          files: [image.file],
          title: "Laufgruppe",
          url,
        });
      } else download();
    } catch (e) {
      if (e.name !== "AbortError") download();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Bild teilen" onClose={onClose}>
      <div className="share-preview" aria-busy={!image && !error}>
        {image ? (
          <img
            src={image.src}
            alt={`${run.distance_km} km · ${pace(run.pace_seconds)} min/km · ${runDate(run.starts_at)} · ${run.meeting_point}. Karte mit Startpunkt.`}
          />
        ) : (
          <p role="status">{error || "Bild wird vorbereitet …"}</p>
        )}
      </div>
      <button
        className="btn primary share-action"
        disabled={!image || busy}
        onClick={share}
      >
        Bild teilen
      </button>
      {status && (
        <p className="muted" role="status">
          {status}
        </p>
      )}
    </Modal>
  );
}
