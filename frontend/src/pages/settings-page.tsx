import { Key, Bell, Palette, Shield } from "lucide-react";

const sections = [
  { icon: Key, title: "API Keys", description: "Manage Sarvam AI, Pinecone, and other service credentials." },
  { icon: Bell, title: "Notifications", description: "Configure filing alerts, sentiment triggers, and digest emails." },
  { icon: Palette, title: "Appearance", description: "Theme, accent colour, and display density preferences." },
  { icon: Shield, title: "Privacy & Security", description: "Data retention policies, session management, and audit log." },
];

export function SettingsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure API keys, notification preferences, and platform settings.
        </p>
      </div>

      <div className="divide-y divide-border rounded-xl border border-border bg-card">
        {sections.map(({ icon: Icon, title, description }) => (
          <div key={title} className="flex items-center gap-4 px-5 py-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted/50 text-muted-foreground">
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-foreground">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
            </div>
            <span className="text-xs text-muted-foreground bg-muted/50 rounded-md px-2 py-0.5">
              Coming soon
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
