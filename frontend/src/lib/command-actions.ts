export interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  url: string;
}

export const pages: CommandItem[] = [
  { id: "page-dashboard", title: "Dashboard", subtitle: "Overview and metrics", icon: "\u{1F3E0}", url: "/" },
  { id: "page-capture", title: "Capture", subtitle: "Data capture tools", icon: "\u{1F4F7}", url: "/capture" },
  { id: "page-vision", title: "Vision", subtitle: "Vision processing", icon: "\u{1F441}", url: "/vision" },
  { id: "page-audio", title: "Audio", subtitle: "Audio processing", icon: "\u{1F3B5}", url: "/audio" },
  { id: "page-transform", title: "Transform", subtitle: "Data transformations", icon: "\u{1F504}", url: "/transform" },
  { id: "page-train", title: "Train", subtitle: "Model training", icon: "\u{1F9E0}", url: "/train" },
  { id: "page-validate", title: "Validate", subtitle: "Validation tools", icon: "\u2705", url: "/validate" },
  { id: "page-search", title: "Search", subtitle: "Search everything", icon: "\u{1F50D}", url: "/search" },
  { id: "page-evaluation", title: "Evaluation", subtitle: "Model evaluation", icon: "\u{1F4CA}", url: "/evaluation" },
  { id: "page-pipeline", title: "Pipeline", subtitle: "Pipeline builder", icon: "\u{1F6E0}", url: "/pipeline" },
  { id: "page-alerts", title: "Alerts", subtitle: "Alert management", icon: "\u{1F514}", url: "/alerts" },
  { id: "page-investigate", title: "Investigate", subtitle: "Investigation tools", icon: "\u{1F50E}", url: "/investigate" },
  { id: "page-agents", title: "Agents", subtitle: "AI agents and Copilot", icon: "\u{1F916}", url: "/agents" },
  { id: "page-assets", title: "Assets", subtitle: "Asset management", icon: "\u{1F4C1}", url: "/assets" },
  { id: "page-settings", title: "Settings", subtitle: "Application settings", icon: "\u2699", url: "/settings" },
  { id: "page-observability", title: "Observability", subtitle: "System observability", icon: "\u{1F4C8}", url: "/observability" },
  { id: "page-profile", title: "Profile", subtitle: "User profile", icon: "\u{1F464}", url: "/profile" },
  { id: "page-developer", title: "Developer", subtitle: "Developer tools", icon: "\u{1F4BB}", url: "/developer" },
];

export const actions: CommandItem[] = [
  { id: "action-start-capture", title: "Start capture", subtitle: "Begin a new capture session", icon: "\u25B6", url: "/capture" },
  { id: "action-new-pipeline", title: "New pipeline", subtitle: "Create a new pipeline", icon: "\u2795", url: "/pipeline" },
  { id: "action-upload-asset", title: "Upload asset", subtitle: "Upload a new asset", icon: "\u{1F4E4}", url: "/assets" },
  { id: "action-ask-copilot", title: "Ask Copilot", subtitle: "Open AI Copilot", icon: "\u{1F4AC}", url: "/agents" },
  { id: "action-create-alert", title: "Create alert rule", subtitle: "Set up a new alert rule", icon: "\u{1F6A8}", url: "/alerts" },
  { id: "action-new-investigation", title: "New investigation", subtitle: "Start a new investigation", icon: "\u{1F50E}", url: "/investigate" },
];
