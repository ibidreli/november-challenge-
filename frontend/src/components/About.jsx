import React, { useEffect, useRef } from "react";
import yanuPortrait from "../../logo/Yänu.png";
import oliPortrait from "../../logo/Oli.png";
import eliPortrait from "../../logo/Eli.png";
import "./About.css";

const members = [
  {
    name: "Yänu",
    role: "Netzwerk & Organisation",
    initial: "Y",
    image: yanuPortrait,
    paragraphs: [
      "Der Netzwerker im OK. Kennt sämtliche wichtigen Entscheidungsträger:innen von Bern bis Zürich. Bei einer Weltmeisterschaft im «Alles unter einen Hut bringen» wäre er ein heisser Anwärter auf die Goldmedaille.",
      "Seine Begeisterungsfähigkeit und sein Ideenreichtum zeichnen ihn aus.",
    ],
  },
  {
    name: "Oli",
    role: "Ideen & Konzept",
    initial: "O",
    image: oliPortrait,
    paragraphs: [
      "Wie bei so manchem Nachwuchstalent im Fussball gilt auch bei ihm: Ohne Verletzungen hätte es für ganz Grosses gereicht. Spuckt zu Beginn der Challenge jeweils grosse Töne, konnte diesen bisher aber noch nie Taten folgen lassen.",
      "Der Kreativkopf im OK, dem die Ideen für zukünftige Ausgaben so schnell nicht ausgehen.",
    ],
  },
  {
    name: "Eli",
    role: "Technik & Umsetzung",
    initial: "E",
    image: eliPortrait,
    paragraphs: [
      "Mister Decathlon und das neuste Mitglied im Organisationskomitee. Setzt technisch um, was sich Yänu und Oli in ihren Köpfen ausmalen, selbst aber beim besten Willen nicht auf die Reihe kriegen.",
      "Hasst Höhenmeter und macht dafür auf flachen Passagen ordentlich Dampf.",
    ],
  },
];

const editions = [
  {
    year: 2025,
    title: "Die Reihenfolge selbst bestimmen",
    description:
      "2025 wurde die Challenge flexibler: Für die volle Punktzahl musste weiterhin an jedem Novembertag ein Lauf absolviert werden. Die Distanzen von 1 bis 30 Kilometern konnten nun aber frei auf die Tage verteilt werden – jede Distanz genau einmal. So liessen sich die Läufe besser planen und die Belastung über den Monat verteilen.",
    finishers: [
      "Valentin Denzler",
      "Eric Lüthi",
      "Andri Wyss",
      "Vincent Notz",
      "Lukas Hohwald",
      "Christoph Meister",
      "Sandro Wicki",
      "Elias Pulver",
      "Samuel Skotta",
    ],
    examples: [
      ["1. November", 17],
      ["2. November", 2],
      ["3. November", 24],
    ],
  },
  {
    year: 2024,
    title: "Jeden Tag einen Kilometer mehr",
    description:
      "2024 gab der Kalender die Distanz vor: Am 1. November stand ein Kilometer auf dem Programm, am 2. zwei, am 3. drei – und so ging es Tag für Tag weiter. Den Abschluss bildeten 30 Kilometer am 30. November. Wer die Challenge vollständig absolvierte, lief an allen 30 Tagen und sammelte insgesamt 465 Kilometer.",
    finishers: ["Franziskus Heinzmann", "Thierry Kneissler"],
  },
];

function BackLink({ returnTo, navigate }) {
  return (
    <a
      className="about-back"
      href={returnTo}
      onClick={(event) => navigate(event, returnTo)}
    >
      <svg
        viewBox="0 0 20 20"
        width="18"
        height="18"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="m8 4-6 6 6 6M2 10h16"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      Zurück zur Challenge
    </a>
  );
}

export default function About({ returnTo, navigate }) {
  const heading = useRef(null);
  useEffect(() => {
    const previousTitle = document.title;
    document.title = "Über uns · November Challenge";
    heading.current.focus({ preventScroll: true });
    return () => {
      document.title = previousTitle;
    };
  }, []);
  return (
    <div className="about-page">
      <BackLink returnTo={returnTo} navigate={navigate} />
      <header className="about-heading">
        <span className="eyebrow">November Jogging Challenge</span>
        <h1 ref={heading} tabIndex={-1}>
          Über uns
        </h1>
        <p>Wir sind das Organisationskomitee der November Challenge.</p>
      </header>

      <section className="about-team" aria-labelledby="team-title">
        <h2 id="team-title">Das OK</h2>
        <div className="about-team-grid">
          {members.map((member) => (
            <article className="about-member" key={member.name}>
              <div className="about-member-heading">
                <div className="about-avatar" aria-hidden="true">
                  {member.image ? (
                    <img
                      src={member.image}
                      alt=""
                      width="80"
                      height="80"
                      loading="lazy"
                      decoding="async"
                    />
                  ) : (
                    member.initial
                  )}
                </div>
                <div>
                  <h3>{member.name}</h3>
                  <span>{member.role}</span>
                </div>
              </div>
              {member.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </article>
          ))}
        </div>
      </section>

      <section className="about-history" aria-labelledby="history-title">
        <h2 id="history-title">Die bisherigen Ausgaben</h2>
        {editions.map((edition) => (
          <article className="about-edition" key={edition.year}>
            <header className="about-edition-heading">
              <h3>{edition.year}</h3>
              <span>{edition.title}</span>
            </header>
            <div className="about-edition-grid">
              <div className="about-edition-copy">
                <p>{edition.description}</p>
                {edition.examples && (
                  <>
                    <table className="about-example">
                      <caption>So konnte der Monat beginnen</caption>
                      <thead>
                        <tr>
                          <th scope="col">Datum</th>
                          <th scope="col">Distanz</th>
                          <th scope="col">Punkte</th>
                        </tr>
                      </thead>
                      <tbody>
                        {edition.examples.map(([day, km]) => (
                          <tr key={day}>
                            <th scope="row">{day}</th>
                            <td>{km} km</td>
                            <td>{km}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="about-example-note">
                      Diese Distanzen waren danach vergeben und konnten im
                      November nicht noch einmal gewertet werden.
                    </p>
                  </>
                )}
              </div>
              <aside
                className="about-finishers"
                aria-labelledby={`finishers-${edition.year}`}
              >
                <h4 id={`finishers-${edition.year}`}>Erfolgreich absolviert</h4>
                <ul>
                  {edition.finishers.map((name) => (
                    <li key={name}>{name}</li>
                  ))}
                </ul>
              </aside>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
