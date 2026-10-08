import logoUrl from "../logo/Logo.png";
import { mapTiles, mapAttribution } from "./mapConfig";
import { pace } from "./time";

const teal = "#07998e",
  ink = "#173b35",
  muted = "#62756f";
const font = (size, weight = 400) => `${weight} ${size}px Arial, sans-serif`;

function loadImage(url, signal) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    const cleanup = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
      image.onload = image.onerror = null;
    };
    const fail = (error) => {
      cleanup();
      image.removeAttribute("src");
      reject(error);
    };
    const abort = () => fail(new DOMException("Cancelled", "AbortError"));
    const timer = setTimeout(() => fail(new Error("Image timeout")), 10000);
    image.onload = () => {
      cleanup();
      resolve(image);
    };
    image.onerror = () => fail(new Error("Image unavailable"));
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) abort();
    else image.src = url;
  });
}

function lines(ctx, value, width) {
  const result = [];
  let line = "";
  for (const word of String(value).trim().split(/\s+/)) {
    if (line && ctx.measureText(line + " " + word).width > width) {
      result.push(line);
      line = "";
    }
    for (const char of (line ? " " : "") + word) {
      if (line && ctx.measureText(line + char).width > width) {
        result.push(line);
        line = "";
      }
      line += char;
    }
  }
  if (line) result.push(line);
  return result;
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

async function drawMap(ctx, run, top, signal) {
  const left = 44,
    width = 452,
    height = 210,
    zoom = 15,
    count = 2 ** zoom;
  const latitude = Math.max(-85.05112878, Math.min(85.05112878, run.latitude));
  const sin = Math.sin((latitude * Math.PI) / 180);
  const centerX = ((run.longitude + 180) / 360) * count * 256;
  const centerY =
    (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * count * 256;
  const originX = centerX - width / 2,
    originY = centerY - height / 2;
  const tiles = [];
  for (
    let x = Math.floor(originX / 256);
    x <= Math.floor((originX + width) / 256);
    x++
  ) {
    for (
      let y = Math.floor(originY / 256);
      y <= Math.floor((originY + height) / 256);
      y++
    ) {
      const tileUrl = mapTiles
        .replace("{z}", zoom)
        .replace("{x}", ((x % count) + count) % count)
        .replace("{y}", Math.max(0, Math.min(count - 1, y)))
        .replace("{s}", "a")
        .replace("{r}", "");
      tiles.push(
        loadImage(tileUrl, signal).then((image) => ({
          image,
          x: x * 256 - originX,
          y: y * 256 - originY,
        })),
      );
    }
  }
  const loaded = await Promise.allSettled(tiles);
  if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
  const available = loaded.every((tile) => tile.status === "fulfilled");
  ctx.save();
  roundRect(ctx, left, top, width, height, 4);
  ctx.clip();
  ctx.fillStyle = "#eaf1ee";
  ctx.fillRect(left, top, width, height);
  if (available) {
    for (const tile of loaded) {
      const { image, x, y } = tile.value;
      ctx.drawImage(image, left + x, top + y, 256, 256);
    }
    ctx.fillStyle = "#ffffffed";
    ctx.fillRect(left, top + height - 22, width, 22);
    const attribution = document.createElement("div");
    attribution.innerHTML = mapAttribution;
    const credits = [
      attribution.textContent,
      ...[...attribution.querySelectorAll("a[href]")].map((a) =>
        a.href.replace(/^https?:\/\//, "").replace(/\/$/, ""),
      ),
    ].join(" · ");
    ctx.fillStyle = "#31423d";
    ctx.font = font(10);
    ctx.textAlign = "right";
    ctx.fillText(credits, left + width - 8, top + height - 7, width - 16);
  } else {
    ctx.fillStyle = muted;
    ctx.font = font(14);
    ctx.textAlign = "center";
    ctx.fillText("Karte gerade nicht verfügbar", left + width / 2, top + 155);
  }
  ctx.restore();
  // Pin and label sit exactly at the projected start coordinates in this viewport.
  const x = left + width / 2,
    y = top + height / 2;
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(x, y, 17, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = teal;
  ctx.beginPath();
  ctx.arc(x, y - 7, 12, Math.PI, 0);
  ctx.lineTo(x, y + 15);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "white";
  ctx.beginPath();
  ctx.arc(x, y - 7, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.textAlign = "left";
  return available;
}

export async function createRunCard(run, url, signal) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas unavailable");
  ctx.font = font(16, 700);
  const meeting = lines(ctx, run.meeting_point, 452);
  ctx.font = font(12);
  const creator = lines(ctx, `Von ${run.creator_name}`, 452);
  const placeTop = 277 + creator.length * 18;
  const mapTop = placeTop + 32 + meeting.length * 22;
  const height = mapTop + 284;
  canvas.width = 1080;
  canvas.height = height * 2;
  ctx.scale(2, 2);
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, 540, height);

  const logo = await loadImage(logoUrl, signal);
  ctx.drawImage(logo, 44, 36, 28, 30);
  ctx.fillStyle = ink;
  ctx.font = font(15, 700);
  ctx.fillText("November Challenge", 84, 56);
  ctx.strokeStyle = "#e5ece8";
  ctx.beginPath();
  ctx.moveTo(44, 86);
  ctx.lineTo(496, 86);
  ctx.stroke();
  ctx.fillStyle = ink;
  ctx.font = font(24, 700);
  ctx.fillText("Laufgruppe", 44, 128);
  ctx.font = font(22);
  ctx.fillText(
    `${run.distance_km} km · ${pace(run.pace_seconds)} min/km`,
    44,
    166,
  );
  ctx.font = font(16, 700);
  ctx.fillText(
    new Date(run.starts_at).toLocaleDateString("de-CH", {
      timeZone: "Europe/Zurich",
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }),
    44,
    207,
    452,
  );
  ctx.fillStyle = muted;
  ctx.font = font(14);
  const time = new Date(run.starts_at).toLocaleTimeString("de-CH", {
    timeZone: "Europe/Zurich",
    hour: "2-digit",
    minute: "2-digit",
  });
  ctx.fillText(`${time} Uhr`, 44, 232);
  ctx.font = font(12);
  creator.forEach((line, i) => ctx.fillText(line, 44, 260 + i * 18));
  ctx.font = font(12);
  ctx.fillText("Treffpunkt", 44, placeTop);
  ctx.fillStyle = ink;
  ctx.font = font(16, 700);
  meeting.forEach((line, i) => ctx.fillText(line, 44, placeTop + 25 + i * 22));
  const mapAvailable = await drawMap(ctx, run, mapTop, signal);
  ctx.fillStyle = muted;
  ctx.font = font(10);
  if (!mapAvailable)
    ctx.fillText(
      `${run.latitude.toFixed(5)}, ${run.longitude.toFixed(5)}`,
      44,
      mapTop + 229,
    );
  ctx.fillStyle = teal;
  ctx.font = font(12);
  const link = new URL(url);
  ctx.fillText(
    `${link.host}${link.pathname}${link.search}`,
    44,
    mapTop + 255,
    452,
  );
  if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
  const blob = await new Promise((resolve) =>
    canvas.toBlob(resolve, "image/png"),
  );
  if (!blob) throw new Error("Image export failed");
  return {
    file: new File([blob], `laufgruppe-${run.id}.png`, { type: "image/png" }),
    mapAvailable,
  };
}
