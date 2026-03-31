import { useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { api } from "./api";
import { KpiTelemetryPanel } from "./components/KpiTelemetryPanel";
import { DailyOutfitPage } from "./pages/DailyOutfitPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";
import { WardrobePage } from "./pages/WardrobePage";
import { trackEvent } from "./telemetry";

export function App() {
  const navigate = useNavigate();
  const [hasProfile, setHasProfile] = useState(false);
  const [hasWardrobe, setHasWardrobe] = useState(false);
  const [hasDailySuggestion, setHasDailySuggestion] = useState(false);
  const [guideLoading, setGuideLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadGuideState() {
      setGuideLoading(true);
      try {
        const [profile, items] = await Promise.all([api.getProfile(), api.listItems()]);
        if (!active) {
          return;
        }
        setHasProfile(Boolean(profile.name || profile.life_phase || profile.figure_analysis || profile.color_profile));
        setHasWardrobe(items.length > 0);
        trackEvent("guided_step_viewed", {
          step_status_profile: Boolean(profile.name || profile.life_phase || profile.figure_analysis || profile.color_profile),
          step_status_wardrobe: items.length > 0,
          step_status_daily: hasDailySuggestion,
        });
      } catch {
        if (!active) {
          return;
        }
        setHasProfile(false);
        setHasWardrobe(false);
      } finally {
        if (active) {
          setGuideLoading(false);
        }
      }
    }

    void loadGuideState();
    return () => {
      active = false;
    };
  }, []);

  const guideProgress = useMemo(() => {
    const done = [hasProfile, hasWardrobe, hasDailySuggestion].filter(Boolean).length;
    return { done, total: 3 };
  }, [hasProfile, hasWardrobe, hasDailySuggestion]);

  function handleContinueSetup() {
    if (!hasProfile) {
      navigate("/dashboard/profile");
      return;
    }
    if (!hasWardrobe) {
      navigate("/dashboard/wardrobe");
      return;
    }
    navigate("/dashboard/daily");
  }

  return (
    <main className="layout">
      <header className="hero heroDashboard">
        <p className="eyebrow">Personal Style OS</p>
        <h1>Wardrobe Studio</h1>
        <p>Your warm, intelligent style workspace: profile, wardrobe, onboarding, daily outfit guidance, and account controls.</p>
      </header>
      <section className="card setupGuide" aria-live="polite">
        <div className="sectionHead">
          <p className="eyebrow">Guided First Run</p>
          <p className="metaNote">
            {guideLoading ? "Checking setup..." : `${guideProgress.done}/${guideProgress.total} steps complete`}
          </p>
        </div>
        <p>Follow this flow for the fastest value: complete identity, add a few wardrobe pieces, then generate your first daily edit.</p>
        <div className="guideSteps">
          <span className={hasProfile ? "guideStep done" : "guideStep"}>1. Profile</span>
          <span className={hasWardrobe ? "guideStep done" : "guideStep"}>2. Wardrobe</span>
          <span className={hasDailySuggestion ? "guideStep done" : "guideStep"}>3. Daily recommendation</span>
        </div>
        <button type="button" onClick={handleContinueSetup}>
          Continue setup
        </button>
      </section>
      <KpiTelemetryPanel />
      <nav className="dashNav" aria-label="Dashboard navigation">
        <NavLink to="/dashboard/profile" className="dashLink">
          1. Identity
        </NavLink>
        <NavLink to="/dashboard/wardrobe" className="dashLink">
          2. Wardrobe Archive
        </NavLink>
        <NavLink to="/dashboard/onboarding" className="dashLink">
          3. Style Onboarding
        </NavLink>
        <NavLink to="/dashboard/daily" className="dashLink">
          4. Daily Edit
        </NavLink>
        <NavLink to="/dashboard/settings" className="dashLink">
          5. Studio Settings
        </NavLink>
      </nav>
      <Routes>
        <Route path="profile" element={<ProfilePage />} />
        <Route path="wardrobe" element={<WardrobePage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route
          path="daily"
          element={
            <DailyOutfitPage
              onGeneratedSuggestion={() => {
                setHasDailySuggestion(true);
                trackEvent("first_suggestion_generated", {
                  source: "daily_page",
                });
              }}
            />
          }
        />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard/profile" replace />} />
      </Routes>
    </main>
  );
}
