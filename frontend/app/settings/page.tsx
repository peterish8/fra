export default function SettingsPage() {
  return (
    <main className="settings-page" id="main-content">
      <header className="settings-topbar"><div><p>Account</p><h1>Workspace settings</h1></div><span>Local demo</span></header>
      <section className="settings-surface" aria-labelledby="settings-preferences"><p className="settings-kicker">Preferences</p><h2 id="settings-preferences">Research defaults</h2><p>Preferences will be stored with your authenticated workspace when the production identity provider is connected.</p></section>
    </main>
  );
}
