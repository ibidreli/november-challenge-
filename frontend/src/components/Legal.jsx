import React, { useEffect, useRef } from "react";
import "./Legal.css";

export default function Legal({ returnTo, navigate }) {
  const heading = useRef(null);
  useEffect(() => {
    const previousTitle = document.title;
    document.title = "AGB & Datenschutz · November Challenge";
    heading.current.focus({ preventScroll: true });
    return () => {
      document.title = previousTitle;
    };
  }, []);

  return (
    <article className="legal-page">
      <a
        className="legal-back"
        href={returnTo}
        onClick={(event) => navigate(event, returnTo)}
      >
        <span aria-hidden="true">←</span> Zurück zur Challenge
      </a>
      <header className="legal-heading">
        <span className="eyebrow">November Jogging Challenge</span>
        <h1 ref={heading} tabIndex={-1}>
          AGB & Datenschutz
        </h1>
        <p>Teilnahmebedingungen und Datenschutzerklärung für novjogcha.ch</p>
        <p className="legal-date">
          Stand: <time dateTime="2026-10-20">20. Oktober 2026</time>
        </p>
      </header>

      <nav className="legal-nav" aria-label="Inhalt der Rechtstexte">
        <a href="#teilnahmebedingungen">Teilnahmebedingungen</a>
        <a href="#datenschutz">Datenschutz</a>
        <a href="#kontakt">Kontakt</a>
      </nav>

      <p className="legal-summary">
        Namen und Challenge-Ergebnisse sowie Angaben zu Laufgruppen sind auf
        dieser Website öffentlich sichtbar. GPS-Laufstrecken werden nicht
        gespeichert oder angezeigt. Diese Informationen und die Verbindung mit
        Strava ersetzen keine gesonderte Einwilligung, soweit eine solche für
        eine Veröffentlichung erforderlich ist.
      </p>

      <section aria-labelledby="teilnahmebedingungen">
        <h2 id="teilnahmebedingungen">Teilnahmebedingungen (AGB)</h2>

        <h3>1. Angebot und Geltungsbereich</h3>
        <p>
          Die November Jogging Challenge ist eine privat organisierte
          Lauf-Challenge in der Schweiz. Diese Bedingungen beschreiben die
          Teilnahme, die Nutzung der Website und der Laufgruppen. Verantwortlich
          für den Betrieb ist Elias Pulver; die vollständigen Kontaktdaten
          stehen
          <a href="#kontakt"> am Ende dieser Seite</a>. Über die Website werden
          keine kostenpflichtigen Buchungen oder Zahlungen abgewickelt.
        </p>
        <p>
          Das blosse Besuchen der Website gilt weder als Annahme von AGB noch
          als Zustimmung zur Veröffentlichung personenbezogener Angaben. Die
          Zustimmung zu Teilnahmebedingungen ist von datenschutzrechtlichen
          Einwilligungen zu unterscheiden. Eine rückwirkende Einwilligung wird
          durch diesen Text nicht begründet.
        </p>

        <h3>2. Teilnahme und faire Nutzung</h3>
        <p>
          Die Teilnahme ist freiwillig. Für die automatische Challenge-Wertung
          wird ein eigenes Strava-Konto verbunden. Laufgruppen können auch ohne
          Strava genutzt werden. Dort darfst du deinen Vornamen oder einen
          Spitznamen verwenden. Trage nur eigene Angaben ein und melde keine
          anderen Personen ohne deren Erlaubnis an. Identitätstäuschung,
          manipulierte Aktivitäten, beleidigende Inhalte und missbräuchliche
          Einträge sind nicht zulässig.
        </p>
        <p>
          Bei Minderjährigen müssen die erforderlichen Zustimmungen der
          gesetzlichen Vertretung vorliegen. Die Alters- und Nutzungsbedingungen
          von Strava gelten unabhängig von dieser Website.
        </p>

        <h3>3. Ablauf und Wertung</h3>
        <p>
          Massgebend sind die auf der Übersicht angegebenen Termine, die
          veröffentlichten Wochen-Auslosungen und die eingestellte
          Abschlussdistanz der jeweiligen Ausgabe. Die Auslosung findet
          ausserhalb der Website statt; das OK trägt die Ergebnisse ein. Die
          Distanzen werden auf vier Zeiträume mit acht, sieben, sieben und
          sieben Feldern verteilt. Die Abschlussdistanz bleibt für den
          Abschlusslauf reserviert.
        </p>
        <p>
          Pro Kalendertag nach Schweizer Zeit zählt der längste einzelne Lauf.
          Er erledigt die grösste noch offene Distanz des zugehörigen Zeitraums,
          die mindestens erreicht wurde. Kürzere Läufe werden nicht
          zusammengerechnet; offene Felder werden nicht in den nächsten Zeitraum
          übertragen. Der Abschlusslauf wird am angegebenen Abschlusstag
          gewertet, wenn mindestens die eingestellte Abschlussdistanz erreicht
          wird.
        </p>
        <p>
          Die Synchronisation hängt von Strava und der technischen Verfügbarkeit
          ab. Ergebnisse können sich durch spätere Importe, gelöschte
          Aktivitäten oder nachvollziehbare Korrekturen ändern. Bei
          Unstimmigkeiten kannst du eine Prüfung durch das OK verlangen.
        </p>

        <h3>4. Laufgruppen und geteilte Inhalte</h3>
        <p>
          Laufgruppen dienen der Verabredung zum gemeinsamen Laufen. Distanz,
          Pace, Treffpunkt und Zeit sind Angaben der erstellenden Person und
          keine Zusicherung des OK. Eine Anmeldung ist keine Garantie, dass der
          Lauf tatsächlich stattfindet oder von einer Fachperson begleitet wird.
          Wähle einen geeigneten, öffentlich zugänglichen Treffpunkt und
          veröffentliche keine vertraulichen Adressen oder Angaben über Dritte.
        </p>
        <p>
          Drei Stunden nach der Startzeit wird ein Lauf nicht mehr öffentlich
          angezeigt. Das ist keine automatische Löschung der gespeicherten
          Daten. Erstellende können ihren Lauf absagen; Teilnehmende können ihre
          Teilnahme mit derselben Browser- oder Kontoverbindung zurückziehen.
          Beim Teilen eines Laufbilds entscheidest du selbst über Empfänger und
          Nachrichtendienst. Beachte dabei die Rechte anderer Personen.
        </p>

        <h3>5. Gesundheit, Sicherheit und Haftung</h3>
        <p>
          Du entscheidest selbst, welche Distanzen deiner Gesundheit und deinem
          Trainingsstand entsprechen. Es besteht keine Pflicht, alle Felder zu
          erfüllen. Beachte Wetter, Strassenverkehr, Wegrechte und behördliche
          Vorgaben. Für ausreichenden Versicherungs- und Unfallschutz bist du
          selbst verantwortlich; über die Website wird keine Versicherung
          abgeschlossen.
        </p>
        <p>
          Wir können keine ununterbrochene Verfügbarkeit oder vollständig
          fehlerfreie Datenübernahme zusichern. Eine Haftung für technische
          Ausfälle und Datenfehler wird nur ausgeschlossen, soweit das Gesetz
          dies erlaubt. Die Haftung für Absicht und grobe Fahrlässigkeit sowie
          andere zwingende gesetzliche Haftungsansprüche bleiben unberührt.
        </p>

        <h3>6. Fotos und Rückblicke</h3>
        <p>
          Eine Teilnahme oder Strava-Verbindung ist keine pauschale Erlaubnis,
          Fotos oder Namen in Rückblicken zu veröffentlichen. Für die Bilder und
          Namenslisten früherer Ausgaben ist eine eigene rechtliche Grundlage
          erforderlich. Eine darauf bezogene Einwilligung kannst du für die
          Zukunft widerrufen. Bei Einwänden gegen ein Foto oder einen
          Namenseintrag wende dich an die unten genannte Kontaktadresse.
        </p>

        <h3>7. Änderungen und anwendbares Recht</h3>
        <p>
          Wesentliche Änderungen am Ablauf oder an diesen Bedingungen werden auf
          der Website mitgeteilt und mit einem neuen Stand versehen. Eine
          erforderliche neue Einwilligung wird dadurch nicht ersetzt. Es gilt
          Schweizer Recht. Zwingende Schutzvorschriften und gesetzliche
          Gerichtsstände bleiben vorbehalten.
        </p>
      </section>

      <section aria-labelledby="datenschutz">
        <h2 id="datenschutz">Datenschutzerklärung</h2>
        <p>
          Diese Erklärung beschreibt die Bearbeitung von Personendaten im
          Zusammenhang mit dieser Website nach dem Schweizer Datenschutzgesetz
          (DSG). Verantwortlich ist Elias Pulver. Du erreichst ihn über die
          <a href="#kontakt"> Kontaktangaben unten</a>.
        </p>

        <h3>1. Welche Daten wir bearbeiten und wozu</h3>
        <ul>
          <li>
            <strong>Website-Betrieb:</strong> Beim Abruf werden technische
            Verbindungsdaten wie IP-Adresse, Zeitpunkt, angefragte Seite und
            Browserangaben durch die beteiligten Dienste verarbeitet. Sie dienen
            der Auslieferung, Fehleranalyse und Missbrauchsabwehr. Die Anwendung
            speichert für Anfragebegrenzungen einen aus der IP-Adresse
            abgeleiteten Hashwert.
          </li>
          <li>
            <strong>Strava-Verbindung:</strong> Wir übernehmen deinen Namen und
            deine Strava-ID und speichern die für die Verbindung nötigen
            Zugriffstokens. Dein Strava-Passwort erhalten wir nicht. Für die
            Wertung speichern wir Aktivitäts-ID, Datum, Startzeit, Distanz und
            den daraus ermittelten Wertungsstatus.
          </li>
          <li>
            <strong>Challenge:</strong> Aus den Aktivitäten entstehen gewertete
            Distanzen, erfüllte Felder, Erfüllungsdaten, Rang und gemeinsame
            Statistiken. Das OK kann Korrekturen vornehmen und Auslosungen
            verwalten. GPS-Tracks und Herzfrequenzdaten werden durch diese
            Website nicht gespeichert oder angezeigt.
          </li>
          <li>
            <strong>Laufgruppen:</strong> Wir speichern den eingegebenen Namen,
            Distanz, gewünschte Pace, Startzeit, Treffpunkt und dessen
            Koordinaten sowie die Teilnahmen. Eine Browserkennung und bei
            angemeldeten Personen die Kontoverknüpfung ermöglichen Bearbeiten,
            Absagen und Austreten. Der Treffpunkt wird bewusst gesetzt; es gibt
            keine laufende GPS-Ortung.
          </li>
          <li>
            <strong>Kontakt und Rückblicke:</strong> Bei einer Anfrage
            bearbeiten wir deine Nachricht und die darin enthaltenen
            Kontaktangaben. Für Rückblicke werden die gezeigten Fotos und Namen
            bearbeitet.
          </li>
        </ul>

        <h3>2. Was öffentlich sichtbar ist</h3>
        <p>
          Die Rangliste ist ohne Anmeldung zugänglich. Sie zeigt Anzeigename,
          Rang, gewertete Challenge-Kilometer, erledigte Distanzen und deren
          Erfüllungsdaten. Der Anzeigename wird bei der ersten Strava-Anmeldung
          aus dem dortigen Namen übernommen. Du kannst deinen echten Namen
          jederzeit durch einen Spitznamen ersetzen lassen. Kontaktiere dafür
          das OK über die
          <a href="#kontakt"> unten angegebenen Kontaktdaten</a> und teile uns
          deinen gewünschten Anzeigenamen mit. Die persönlichen Zugriffstokens
          und die vollständigen importierten Aktivitäten sind nicht Bestandteil
          der öffentlichen Rangliste.
        </p>
        <p>
          Bei aktiven Laufgruppen sind Name der erstellenden Person,
          Teilnahmenamen, Distanz, Pace, Datum, Zeit und Treffpunkt samt Karte
          öffentlich. Auf der Seite «Über uns» stehen Fotos und Namen aus
          früheren Ausgaben. Öffentliche Inhalte können auch von Suchmaschinen
          erfasst, kopiert oder von anderen geteilt werden. Eine spätere
          Entfernung von dieser Website entfernt nicht automatisch Kopien bei
          Dritten.
        </p>
        <p>
          Die Bearbeitung erfolgt für den erkennbaren Zweck der
          Challenge-Durchführung, der Verabredung zu Läufen und des sicheren
          Website-Betriebs. Wo eine Einwilligung nötig ist, muss sie informiert,
          freiwillig und für den konkreten Zweck erteilt werden. Das Lesen
          dieser Erklärung und die Strava-Freigabe allein stellen keine
          pauschale Einwilligung zu sämtlichen Veröffentlichungen dar.
        </p>

        <h3>3. Strava und Widerruf der Verbindung</h3>
        <p>
          Strava, Inc. (USA) ermöglicht die Anmeldung und liefert nach deiner
          Freigabe Aktivitätsdaten. Die angefragte Berechtigung umfasst auch
          private Aktivitäten; deren Laufdatum und Distanz können damit in die
          Challenge-Wertung einfliessen. Die Datenschutzeinstellungen eines
          privaten Strava-Profils machen unsere öffentliche Rangliste nicht
          automatisch privat. Massgebend ist zusätzlich die
          <a href="https://www.strava.com/legal/privacy">
            {" "}
            Datenschutzerklärung von Strava
          </a>
          .
        </p>
        <p>
          Du kannst den Zugriff in den Strava-Einstellungen unter den
          verbundenen Apps widerrufen. Ohne gültigen Zugriff können keine neuen
          Aktivitäten importiert werden. Bereits gespeicherte Angaben werden
          dadurch nicht automatisch gelöscht. «Abmelden» auf unserer Website
          beendet lediglich die aktuelle Website-Sitzung. Für die Entfernung
          gespeicherter Daten oder öffentlicher Einträge kontaktiere uns bitte.
        </p>

        <h3>4. Empfänger, Dienste und Bearbeitung im Ausland</h3>
        <p>
          Zugriff auf nicht öffentliche Daten haben die für Betrieb und
          Organisation zuständigen Personen, soweit dies für ihre Aufgaben nötig
          ist. Zusätzlich setzen wir folgende Dienste ein:
        </p>
        <ul>
          <li>
            <strong>Render (USA):</strong> Hosting von Website, Backend und
            Datenbank. Backend und Datenbank werden in Oregon, USA, betrieben;
            die Website kann über ein weltweites Auslieferungsnetz abgerufen
            werden. Render bearbeitet dabei gespeicherte Anwendungsdaten und
            technische Verbindungsdaten. Sein
            <a href="https://render.com/dpa"> Datenbearbeitungszusatz</a>{" "}
            beschreibt die vertraglichen Schutzmassnahmen einschliesslich
            Standardvertragsklauseln und Anpassungen für die Schweiz.
          </li>
          <li>
            <strong>OpenStreetMap Foundation (Vereinigtes Königreich):</strong>{" "}
            Beim Laden einer Karte, auch für ein Laufbild, ruft dein Browser
            Kartenkacheln direkt ab. Dabei werden unter anderem IP-Adresse,
            Browserangaben und der angefragte Kartenausschnitt übermittelt. Die
            Kartenauslieferung nutzt weltweit verteilte Server; sonstige Daten
            werden laut Anbieter im Vereinigten Königreich und den Niederlanden
            gespeichert. Es gilt die
            <a href="https://osmfoundation.org/wiki/Privacy_Policy">
              {" "}
              Datenschutzerklärung der OpenStreetMap Foundation
            </a>
            .
          </li>
          <li>
            <strong>Google/Gmail (Irland und USA):</strong> E-Mails an die
            Kontaktadresse werden über Gmail bearbeitet. Dabei erhält Google
            Nachrichteninhalt und Kommunikationsdaten; eine Bearbeitung in den
            USA ist möglich. Weitere Angaben stehen in der
            <a href="https://policies.google.com/privacy?hl=de">
              {" "}
              Datenschutzerklärung von Google
            </a>
            .
          </li>
        </ul>
        <p>
          Datenbearbeitungen können somit ausserhalb der Schweiz stattfinden,
          insbesondere in den USA, im Vereinigten Königreich, in Irland und den
          Niederlanden. Für Übermittlungen in Staaten ohne anerkannt
          angemessenes Datenschutzniveau sind die gesetzlichen Voraussetzungen
          und geeignete Garantien zu beachten. Auskünfte zu den für eine
          Übermittlung eingesetzten Garantien kannst du bei uns verlangen. Bei
          selbst ausgewählten Nachrichtendiensten zum Teilen gelten zusätzlich
          deren eigene Datenschutzbestimmungen.
        </p>

        <h3>5. Cookies und Browser-Speicher</h3>
        <p>
          Wir verwenden funktionale Cookies für die Anmeldung, die Absicherung
          der Strava-Verbindung und die Wiedererkennung als Gast. Anmeldung und
          Gastkennung haben eine Laufzeit von bis zu 90 Tagen; die
          Anmeldesitzung kann bei weiterer Nutzung verlängert werden. Das
          Sicherheitscookie für den Strava-Anmeldevorgang gilt höchstens zehn
          Minuten. Für die Admin-Anmeldung wird ein Zugangstoken im lokalen
          Browser-Speicher abgelegt und beim Abmelden entfernt.
        </p>
        <p>
          Auf dieser Website sind keine eigenen Werbe- oder Analyse-Tracker
          eingebunden. Schriften werden lokal ausgeliefert. Externe Dienste wie
          Strava, Kartenanbieter oder Nachrichtendienste unterliegen ihren
          eigenen Bestimmungen. Du kannst Cookies im Browser löschen oder
          blockieren; dadurch können Anmeldung und Gastfunktionen entfallen.
        </p>

        <h3>6. Aufbewahrung und Löschung</h3>
        <p>
          Wir bewahren Personendaten nur so lange auf, wie sie für Durchführung,
          Nachkontrolle und nachvollziehbare Dokumentation der jeweiligen
          Ausgabe benötigt werden oder gesetzliche Pflichten beziehungsweise
          berechtigte Rechtsansprüche eine weitere Aufbewahrung verlangen.
          Entfällt der Zweck, sind die Daten zu löschen oder zu anonymisieren.
          Persönliche Daten werden nicht allein deshalb unbefristet benötigt,
          weil eine frühere Ausgabe dokumentiert werden soll.
        </p>
        <p>
          Die Website hat derzeit keine automatische Löschfrist für
          Challenge-Aktivitäten, historische Namenslisten, Fotos oder
          abgelaufene Laufgruppen. Insbesondere bedeutet das Ausblenden einer
          Laufgruppe nach drei Stunden keine Löschung aus der Datenbank.
          Löschungs- und Anonymisierungsanfragen bearbeiten wir über die
          Kontaktadresse. Sicherungskopien und fremde Kopien können zeitversetzt
          entfernt werden; eine absolute Löschung bereits geteilter Inhalte
          können wir nicht zusichern.
        </p>

        <h3>7. Deine Rechte</h3>
        <p>
          Du kannst Auskunft über die bearbeiteten Personendaten verlangen,
          falsche Angaben berichtigen lassen und eine Löschung oder
          Anonymisierung beantragen. Du kannst einer Bearbeitung widersprechen
          und eine erteilte Einwilligung für die Zukunft widerrufen. Unter den
          gesetzlichen Voraussetzungen besteht ein Recht auf Datenherausgabe
          oder -übertragung. Gesetzliche Aufbewahrungspflichten und andere
          zulässige Rechtfertigungsgründe bleiben vorbehalten.
        </p>
        <p>
          Schreibe an die unten genannte E-Mail-Adresse und beschreibe den
          betroffenen Eintrag. Zum Schutz vor unberechtigten Anfragen kann ein
          angemessener Identitätsnachweis nötig sein. Weitere Informationen zu
          deinen Rechten erhältst du beim
          <a href="https://www.edoeb.admin.ch/de/meine-rechte-kennen-und-durchsetzen">
            {" "}
            Eidgenössischen Datenschutz- und Öffentlichkeitsbeauftragten (EDÖB)
          </a>
          .
        </p>

        <h3>8. Änderungen dieser Erklärung</h3>
        <p>
          Bei Änderungen an Datenbearbeitungen passen wir diese Erklärung und
          das oben angegebene Datum an. Wesentliche Änderungen werden angemessen
          mitgeteilt. Eine notwendige neue Einwilligung wird dadurch nicht
          ersetzt.
        </p>
      </section>

      <section className="legal-contact" aria-labelledby="kontakt">
        <h2 id="kontakt">Verantwortliche Stelle und Kontakt</h2>
        <address>
          Elias Pulver
          <br />
          Mülchistrasse 4
          <br />
          3317 Limpach
          <br />
          Schweiz
          <br />
          <a href="mailto:eliaspulver@gmail.com">eliaspulver@gmail.com</a>
        </address>
        <p>
          Für Fragen zur Teilnahme, den Wechsel zu einem Spitznamen,
          Korrekturen, Datenschutzanfragen, Einwilligungswiderrufe und die
          Entfernung von Namen oder Fotos.
        </p>
      </section>
      <a
        className="legal-back legal-bottom-back"
        href={returnTo}
        onClick={(event) => navigate(event, returnTo)}
      >
        <span aria-hidden="true">←</span> Zurück zur Challenge
      </a>
    </article>
  );
}
