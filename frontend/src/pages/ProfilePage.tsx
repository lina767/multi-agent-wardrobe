import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { UserProfile } from "../types";

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [name, setName] = useState("");
  const [age, setAge] = useState<number | "">("");
  const [lifePhase, setLifePhase] = useState("");
  const [coldSensitivity, setColdSensitivity] = useState<number | "">(3);
  const [figureAnalysis, setFigureAnalysis] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  async function loadProfile() {
    setError(null);
    try {
      const data = await api.getProfile();
      setProfile(data);
      setName(data.name ?? "");
      setAge(data.age ?? "");
      setLifePhase(data.life_phase ?? "");
      setColdSensitivity(data.cold_sensitivity ?? 3);
      setFigureAnalysis(data.figure_analysis ?? "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load profile.");
    }
  }

  useEffect(() => {
    void loadProfile();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateProfile({
        name: name.trim() || undefined,
        age: age === "" ? undefined : Number(age),
        life_phase: lifePhase.trim() || undefined,
        cold_sensitivity: coldSensitivity === "" ? undefined : Number(coldSensitivity),
        figure_analysis: figureAnalysis.trim() || undefined,
      });
      setProfile(updated);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSelfieUpload(file: File | null) {
    if (!file) {
      return;
    }
    setError(null);
    try {
      const updated = await api.uploadProfileSelfie(file);
      setProfile(updated);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Selfie upload failed.");
    }
  }

  async function handleAnalyze(file: File | null) {
    if (!file) {
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyzeFigurePhoto(file);
      const summary = `${result.season} / ${result.undertone} / contrast ${result.contrast_level}`;
      setFigureAnalysis(summary);
      const updated = await api.updateProfile({ figure_analysis: summary });
      setProfile(updated);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Figure analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Profile</p>
      </div>
      <h2>Identity Profile</h2>
      {error ? <p className="error">{error}</p> : null}
      <form className="grid" data-dashboard-save="true" onSubmit={handleSubmit}>
        <label className="field">
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="field">
          Age
          <input type="number" min={1} max={120} value={age} onChange={(event) => setAge(event.target.value ? Number(event.target.value) : "")} />
        </label>
        <label className="field">
          Life chapter
          <input value={lifePhase} onChange={(event) => setLifePhase(event.target.value)} />
        </label>
        <label className="field">
          Cold sensitivity (1 = rarely cold, 5 = gets cold quickly)
          <input
            type="number"
            min={1}
            max={5}
            value={coldSensitivity}
            onChange={(event) => setColdSensitivity(event.target.value ? Number(event.target.value) : "")}
          />
        </label>
        <label className="field">
          Silhouette notes
          <input value={figureAnalysis} onChange={(event) => setFigureAnalysis(event.target.value)} />
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save profile"}
        </button>
      </form>
      <div className="row">
        <label className="uploadButton">
          Upload selfie
          <input type="file" accept="image/*" onChange={(event) => void handleSelfieUpload(event.target.files?.[0] ?? null)} />
        </label>
        <label className="uploadButton">
          {analyzing ? "Analyzing..." : "Analyze silhouette"}
          <input type="file" accept="image/*" onChange={(event) => void handleAnalyze(event.target.files?.[0] ?? null)} />
        </label>
      </div>
      {profile?.selfie_url ? <img src={profile.selfie_url} alt="Selfie" className="profileSelfie" /> : null}
      {profile?.color_profile ? (
        <p className="metaNote">
          Color signature: {profile.color_profile.season} / {profile.color_profile.undertone} / {profile.color_profile.contrast_level}
        </p>
      ) : null}
    </section>
  );
}
