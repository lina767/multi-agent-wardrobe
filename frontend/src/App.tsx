import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { DailyOutfitPage } from "./pages/DailyOutfitPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";
import { WardrobePage } from "./pages/WardrobePage";

export function App() {
  return (
    <main className="layout">
      <header className="hero">
        <h1>Wardrobe Studio</h1>
        <p>Your warm, intelligent style workspace: profile, wardrobe, onboarding, daily outfit guidance, and account controls.</p>
      </header>
      <nav className="dashNav">
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
        <Route path="daily" element={<DailyOutfitPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard/profile" replace />} />
      </Routes>
    </main>
  );
}
