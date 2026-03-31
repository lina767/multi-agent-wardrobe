import { Link } from "react-router-dom";

export function PublicHome() {
  return (
    <main className="layout">
      <section className="hero heroLanding">
        <p className="eyebrow">Fashion Intelligence</p>
        <h1>Wardrobe Intelligence, with Koselig Warmth</h1>
        <p>A calm editorial platform for thoughtful outfit decisions, shaped by personal context and practical intelligence.</p>
        <div className="row">
          <Link className="linkButton" to="/login">
            Continue with magic link
          </Link>
          <Link className="linkButton subtle" to="/login">
            Open style studio (login required)
          </Link>
        </div>
      </section>
    </main>
  );
}
