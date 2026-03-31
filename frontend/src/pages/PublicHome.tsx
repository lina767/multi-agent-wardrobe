import { Link } from "react-router-dom";

export function PublicHome() {
  return (
    <>
      <header className="landingTopbar">
        <div className="landingTopbarInner">
          <p className="landingBrand">Multi-Agent Wardrobe</p>
          <nav className="landingNav">
            <a href="#funktionen">Funktionen</a>
            <a href="#ablauf">Ablauf</a>
            <a href="#faq">FAQ</a>
          </nav>
          <Link className="linkButton subtle" to="/login">
            Login
          </Link>
        </div>
      </header>

      <main className="layout landingLayout">
        <section className="hero heroLanding landingHero">
          <p className="eyebrow">Fashion Intelligence Platform</p>
          <h1>Dein digitaler Kleiderschrank mit persoenlicher Outfit-Intelligenz</h1>
          <p>
            Multi-Agent Wardrobe verbindet Profil, Wetter, Anlass und deinen Bestand in einer Plattform. So bekommst du taeglich erklaerbare Outfit-Vorschlaege,
            verwaltest deinen Schrank strukturiert und entwickelst deinen Stil datenbasiert weiter.
          </p>
          <div className="row">
            <Link className="linkButton" to="/login">
              Jetzt starten
            </Link>
            <a className="linkButton subtle" href="#funktionen">
              Funktionen entdecken
            </a>
          </div>
          <div className="landingStatGrid">
            <article className="landingStat">
              <p className="landingStatValue">Top-3</p>
              <p>Outfit-Vorschlaege pro Anfrage mit Bewertung und Begruendung</p>
            </article>
            <article className="landingStat">
              <p className="landingStatValue">360°</p>
              <p>Abdeckung von Profil, Kleiderschrank, Feedback und Tageskontext</p>
            </article>
            <article className="landingStat">
              <p className="landingStatValue">Live</p>
              <p>Wetterbezogene Empfehlungen inklusive Signal- und Score-Aufschluesselung</p>
            </article>
          </div>
        </section>

        <section id="funktionen" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">Alle Funktionen</p>
          </div>
          <h2>Alles, was du fuer intelligente Outfit-Entscheidungen brauchst</h2>
          <div className="landingFeatureGrid">
            <article className="landingFeature">
              <h3>Style Onboarding</h3>
              <p>Lege Name, Lebensphase, Stilrichtung und Standort als Basis fuer alle spaeteren Empfehlungen fest.</p>
            </article>
            <article className="landingFeature">
              <h3>Identity Profile</h3>
              <p>Pflege dein Profil laufend, lade ein Portraet hoch und ergaenze Silhouette- bzw. Koerperanalyse.</p>
            </article>
            <article className="landingFeature">
              <h3>Wardrobe Archive</h3>
              <p>Verwalte einzelne Kleidungsstuecke, Bilder, Kategorien, Farben, Wetter-Tags und Formalitaet zentral.</p>
            </article>
            <article className="landingFeature">
              <h3>Bulk Import</h3>
              <p>Importiere mehrere Bilder auf einmal, damit dein Schrank schnell mit analysierbaren Teilen gefuellt ist.</p>
            </article>
            <article className="landingFeature">
              <h3>Daily Edit</h3>
              <p>Erhalte taeglich drei Outfit-Kombinationen auf Basis von Mood, Anlass, Standort und Wetterlage.</p>
            </article>
            <article className="landingFeature">
              <h3>Erklaerbare Scores</h3>
              <p>Jeder Vorschlag zeigt Transparenz ueber Farbe, Stil, Kontext und Nachhaltigkeit als einzelne Werte.</p>
            </article>
            <article className="landingFeature">
              <h3>Feedback-Loop</h3>
              <p>Markiere Vorschlaege als Accept/Skip, vergebe Ratings und trainiere damit die Qualitaet kuenftiger Empfehlungen.</p>
            </article>
            <article className="landingFeature">
              <h3>Outfit Logging</h3>
              <p>Speichere getragene Looks mit einem Klick und baue so eine verlaessliche Style-Historie auf.</p>
            </article>
            <article className="landingFeature">
              <h3>Filter & Sortierung</h3>
              <p>Durchsuche deinen Bestand nach Kategorie, Farbwelt, Wetter-Tags und Sortierlogik fuer schnellen Zugriff.</p>
            </article>
            <article className="landingFeature">
              <h3>Studio Settings</h3>
              <p>Verwalte dein Konto, aktualisiere E-Mail-Informationen und halte deinen Zugang sauber organisiert.</p>
            </article>
          </div>
        </section>

        <section id="ablauf" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">So funktioniert es</p>
          </div>
          <h2>Von der Einrichtung bis zum taeglichen Outfit in 4 Schritten</h2>
          <div className="landingSteps">
            <article className="landingStepCard">
              <p className="landingStepNumber">01</p>
              <h3>Onboarden</h3>
              <p>Basisdaten und Stilkontext erfassen, damit die Plattform deine Ausgangssituation versteht.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">02</p>
              <h3>Schrank aufbauen</h3>
              <p>Teile manuell anlegen oder per Bulk-Upload importieren, inklusive Bild und Metadaten.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">03</p>
              <h3>Daily Edit erzeugen</h3>
              <p>Mood, Anlass und Ort waehlen und sofort drei datengetriebene Outfit-Vorschlaege erhalten.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">04</p>
              <h3>Rueckmelden & verbessern</h3>
              <p>Akzeptieren, bewerten oder als getragen loggen - damit dein System laufend dazulernt.</p>
            </article>
          </div>
        </section>

        <section className="card pageSection landingSection landingCta">
          <div>
            <p className="eyebrow">Bereit fuer bessere Outfit-Entscheidungen?</p>
            <h2>Starte deinen intelligenten Style-Workflow heute</h2>
            <p>
              Die Plattform ist darauf ausgelegt, aus deinem realen Alltag zu lernen - nicht aus generischen Moodboards. Login per Magic Link, Onboarding ausfuellen
              und direkt den ersten Daily Edit erzeugen.
            </p>
          </div>
          <div className="row">
            <Link className="linkButton" to="/login">
              Kostenlos anmelden
            </Link>
            <a className="linkButton subtle" href="#faq">
              Haeufige Fragen
            </a>
          </div>
        </section>

        <section id="faq" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">FAQ</p>
          </div>
          <h2>Haeufige Fragen</h2>
          <div className="landingFaq">
            <article>
              <h3>Brauche ich sofort viele Kleidungsstuecke?</h3>
              <p>Nein. Schon mit 3-5 Kernteilen kannst du starten. Mit mehr Teilen werden die Kombinationen praeziser und vielseitiger.</p>
            </article>
            <article>
              <h3>Kann ich Empfehlungen nachvollziehen?</h3>
              <p>Ja. Jeder Vorschlag zeigt eine textliche Erklaerung sowie Teil-Scores fuer Farbe, Stil, Kontext und Nachhaltigkeit.</p>
            </article>
            <article>
              <h3>Beruecksichtigt das System Tageskontext?</h3>
              <p>Ja. Mood, Anlass, Standort und Wetterdaten fliessen direkt in die taeglichen Outfit-Vorschlaege ein.</p>
            </article>
            <article>
              <h3>Wie wird das System mit der Zeit besser?</h3>
              <p>Durch dein Feedback (Accept, Skip, Rating) und durch geloggte Outfits lernt die Plattform deinen Stil kontinuierlich genauer kennen.</p>
            </article>
          </div>
        </section>
      </main>
    </>
  );
}
