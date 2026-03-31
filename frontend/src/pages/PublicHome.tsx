import { Link } from "react-router-dom";

export function PublicHome() {
  return (
    <main className="layout">
      <section className="hero">
        <h1>Wardrobe Intelligence</h1>
        <p>Public website for your AI-powered wardrobe experience.</p>
        <div className="row">
          <Link className="linkButton" to="/login">
            Login with magic link
          </Link>
          <Link className="linkButton subtle" to="/dashboard">
            Open dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
