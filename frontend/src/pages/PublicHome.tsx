import { Link } from "react-router-dom";

export function PublicHome() {
  return (
    <>
      <header className="landingTopbar">
        <div className="landingTopbarInner">
          <p className="landingBrand">Multi-Agent Wardrobe</p>
          <nav className="landingNav">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
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
          <h1>Your digital wardrobe with personalized outfit intelligence</h1>
          <p>
            Multi-Agent Wardrobe combines profile data, weather, occasion, and your wardrobe in one platform. Get explainable daily outfit recommendations,
            manage your closet with structure, and improve your style with data-backed feedback loops.
          </p>
          <div className="row">
            <Link className="linkButton" to="/login">
              Get started
            </Link>
            <a className="linkButton subtle" href="#features">
              Explore features
            </a>
          </div>
          <div className="landingStatGrid">
            <article className="landingStat">
              <p className="landingStatValue">Top-3</p>
              <p>Outfit recommendations per request, each with scoring and rationale</p>
            </article>
            <article className="landingStat">
              <p className="landingStatValue">360°</p>
              <p>Coverage across profile, wardrobe, feedback, and daily context</p>
            </article>
            <article className="landingStat">
              <p className="landingStatValue">Live</p>
              <p>Weather-aware recommendations with transparent signal and score breakdowns</p>
            </article>
          </div>
        </section>

        <section id="features" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">All Features</p>
          </div>
          <h2>Everything you need for intelligent outfit decisions</h2>
          <div className="landingFeatureGrid">
            <article className="landingFeature">
              <h3>Style Onboarding</h3>
              <p>Set your name, life phase, style direction, and location as the baseline for future recommendations.</p>
            </article>
            <article className="landingFeature">
              <h3>Identity Profile</h3>
              <p>Continuously refine your profile, upload a portrait, and enrich your silhouette or body analysis.</p>
            </article>
            <article className="landingFeature">
              <h3>Wardrobe Archive</h3>
              <p>Manage clothing items, photos, categories, colors, weather tags, and formality in one place.</p>
            </article>
            <article className="landingFeature">
              <h3>Bulk Import</h3>
              <p>Import multiple images at once to quickly populate your closet with analyzable items.</p>
            </article>
            <article className="landingFeature">
              <h3>Daily Edit</h3>
              <p>Get three daily outfit combinations based on mood, occasion, location, and weather conditions.</p>
            </article>
            <article className="landingFeature">
              <h3>Explainable Scores</h3>
              <p>Every suggestion exposes color, style, context, and sustainability as transparent sub-scores.</p>
            </article>
            <article className="landingFeature">
              <h3>Feedback Loop</h3>
              <p>Mark suggestions as accept/skip, add ratings, and continuously improve future recommendation quality.</p>
            </article>
            <article className="landingFeature">
              <h3>Outfit Logging</h3>
              <p>Save worn looks with one click and build a reliable style history over time.</p>
            </article>
            <article className="landingFeature">
              <h3>Filter & Sorting</h3>
              <p>Search your wardrobe by category, color family, weather tags, and sorting logic for fast access.</p>
            </article>
            <article className="landingFeature">
              <h3>Studio Settings</h3>
              <p>Manage your account, update email details, and keep your access setup clean and organized.</p>
            </article>
          </div>
        </section>

        <section id="how-it-works" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">How it works</p>
          </div>
          <h2>From setup to daily outfits in 4 steps</h2>
          <div className="landingSteps">
            <article className="landingStepCard">
              <p className="landingStepNumber">01</p>
              <h3>Onboard</h3>
              <p>Capture core profile and style context so the platform understands your baseline.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">02</p>
              <h3>Build your wardrobe</h3>
              <p>Add items manually or import in bulk, including images and metadata.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">03</p>
              <h3>Generate Daily Edit</h3>
              <p>Choose mood, occasion, and location to instantly receive three data-driven outfit suggestions.</p>
            </article>
            <article className="landingStepCard">
              <p className="landingStepNumber">04</p>
              <h3>Give feedback & improve</h3>
              <p>Accept, rate, or log as worn so the system continuously learns your preferences.</p>
            </article>
          </div>
        </section>

        <section className="card pageSection landingSection landingCta">
          <div>
            <p className="eyebrow">Ready for better outfit decisions?</p>
            <h2>Start your intelligent style workflow today</h2>
            <p>
              The platform is designed to learn from your real daily life, not generic moodboards. Sign in with magic link or password, complete onboarding, and generate
              your first Daily Edit immediately.
            </p>
          </div>
          <div className="row">
            <Link className="linkButton" to="/login">
              Sign up free
            </Link>
            <a className="linkButton subtle" href="#faq">
              FAQ
            </a>
          </div>
        </section>

        <section id="faq" className="card pageSection landingSection">
          <div className="sectionHead">
            <p className="eyebrow">FAQ</p>
          </div>
          <h2>Frequently Asked Questions</h2>
          <div className="landingFaq">
            <article>
              <h3>Do I need a lot of clothing items to start?</h3>
              <p>No. You can start with 3-5 core items. More items make combinations more precise and versatile.</p>
            </article>
            <article>
              <h3>Can I understand why recommendations are shown?</h3>
              <p>Yes. Every suggestion includes a text explanation and sub-scores for color, style, context, and sustainability.</p>
            </article>
            <article>
              <h3>Does the system include daily context?</h3>
              <p>Yes. Mood, occasion, location, and weather signals directly influence daily outfit suggestions.</p>
            </article>
            <article>
              <h3>How does the system improve over time?</h3>
              <p>Through your feedback (accept, skip, rating) and logged outfits, the platform continuously learns your style more accurately.</p>
            </article>
          </div>
        </section>
      </main>
    </>
  );
}
