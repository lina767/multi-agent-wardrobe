import { Link } from "react-router-dom";

export function PublicHome() {
  return (
    <main className="layout">
      <section className="hero">
        <h1>Wardrobe Intelligence, with Koselig Warmth</h1>
        <p>A calm editorial platform for thoughtful outfit decisions, shaped by personal context and practical intelligence.</p>
        <div className="row">
          <Link className="linkButton" to="/login">
            Continue with magic link
          </Link>
          <Link className="linkButton subtle" to="/dashboard">
            Enter style studio
          </Link>
        </div>
      </section>
    </main>
  );
}
