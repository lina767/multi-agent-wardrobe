import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth/AuthProvider";

export function SettingsPage() {
  const { user, updatePassword } = useAuth();
  const [email, setEmail] = useState("");
  const [emailStatus, setEmailStatus] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [savingEmail, setSavingEmail] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
    }
  }, [user?.email]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingEmail(true);
    setEmailStatus(null);
    setEmailError(null);
    try {
      const result = await api.updateEmail(email.trim());
      setEmailStatus(`Email updated to ${result.email ?? "unknown"}`);
    } catch (requestError) {
      setEmailError(requestError instanceof Error ? requestError.message : "Unable to update email.");
    } finally {
      setSavingEmail(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordStatus(null);
    setPasswordError(null);
    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }
    setSavingPassword(true);
    try {
      await updatePassword(newPassword);
      setNewPassword("");
      setConfirmPassword("");
      setPasswordStatus("Password updated successfully.");
    } catch (requestError) {
      setPasswordError(requestError instanceof Error ? requestError.message : "Unable to update password.");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <section className="card pageSection">
      <div className="sectionHead">
        <p className="eyebrow">Account</p>
      </div>
      <h2>Studio Settings</h2>
      {user?.email ? <p className="metaNote">Currently signed in as {user.email}</p> : null}
      <section className="card wardrobeBlock">
        <div className="sectionHead">
          <p className="eyebrow">Email</p>
        </div>
        <form className="grid" onSubmit={handleSubmit}>
          <label className="field">
            Email address
            <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <button type="submit" disabled={savingEmail}>
            {savingEmail ? "Updating..." : "Update email"}
          </button>
        </form>
        {emailStatus ? <p>{emailStatus}</p> : null}
        {emailError ? <p className="error">{emailError}</p> : null}
      </section>
      <section className="card wardrobeBlock">
        <div className="sectionHead">
          <p className="eyebrow">Password</p>
        </div>
        <form className="grid" onSubmit={handlePasswordSubmit}>
          <label className="field">
            New password
            <input type={showPasswords ? "text" : "password"} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </label>
          <label className="field">
            Confirm new password
            <input
              type={showPasswords ? "text" : "password"}
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
          <button type="button" className="linkButton subtle" onClick={() => setShowPasswords((prev) => !prev)}>
            {showPasswords ? "Hide passwords" : "Show passwords"}
          </button>
          <button type="submit" disabled={savingPassword}>
            {savingPassword ? "Updating..." : "Change password"}
          </button>
        </form>
        {passwordStatus ? <p>{passwordStatus}</p> : null}
        {passwordError ? <p className="error">{passwordError}</p> : null}
      </section>
    </section>
  );
}
