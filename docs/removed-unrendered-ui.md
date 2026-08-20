# Removed unrendered UI

On 2026-08-20 the console carried 342 component files. **145 of them were not
imported by any file in the tree** - no page, no sibling component, no barrel, no
dynamic import named their path. Without an import there is no render path, by
JSX or by lookup table, so none of this code had ever run. It was removed.

**145 files, 38,790 lines.** 197 component files remain.

## Why remove rather than wire

An unimported component has never run: no test covers it, no page has satisfied
its props, no reviewer has seen it against real data. Wiring 145 of them is
feature work measured in weeks. Keeping them made the component tree look about
40% larger than the app, and that gap cost real time - an e2e journey was
written against controls belonging to `AudioTransformStudio`, a 1,020-line panel
the transform page imported and never rendered, and sat `fixme` for a round
describing a collapsed section that existed on no page.

## How the set was chosen

The obvious rule - "nothing renders `<Name`" - is wrong, and wrongly deleting
ten working components is how that was found. `OperationControls` renders its
children through a lookup table:

```ts
const CONTROLS = { background_remove: BackgroundRemoveControls, ... };
```

No `<BackgroundRemoveControls` appears anywhere, and it renders on every visit to
the transform page. Aliased imports break that rule too:
`import DetectionTabComponent from ".../DetectionTab"`.

An *import* is necessary for any render path, so that is the rule used here and
enforced by `frontend/src/lib/__tests__/no-unrendered-components.test.ts`.
Deleting a file cascades - it can orphan what only it imported - so the sweep
was run to a fixpoint.

## Getting one back

```bash
git log --diff-filter=D -- frontend/src/components/<dir>/<Name>.tsx
git show <commit>^:frontend/src/components/<dir>/<Name>.tsx
```

Restoring one deliberately and rendering it is a smaller job than it looks - the
code is intact in history. What is gone is the impression that it was wired.

## What was removed

### agents (7)

| Component | Lines |
| --- | ---: |
| `ConversationHistory` | 302 |
| `NewAgentModal` | 289 |
| `VoiceInput` | 207 |
| `PatrolModePanel` | 190 |
| `LiveContextPanel` | 181 |
| `AttachmentInput` | 157 |
| `StarterPrompts` | 108 |

### alerts (5)

| Component | Lines |
| --- | ---: |
| `AlertDetailPanel` | 573 |
| `NotificationChannels` | 557 |
| `RuleBuilderModal` | 547 |
| `AlertRulesTab` | 324 |
| `EscalationPanel` | 129 |

### annotate (7)

| Component | Lines |
| --- | ---: |
| `LabelManagerModal` | 402 |
| `AnnotationListPanel` | 269 |
| `KeyboardShortcutsTooltip` | 193 |
| `ZoomControls` | 188 |
| `UndoRedoControls` | 161 |
| `ExportFormatSelector` | 132 |
| `AutoLabelSuggestions` | 118 |

### assets (4)

| Component | Lines |
| --- | ---: |
| `AssetDetailPanel` | 654 |
| `CollectionsSidebar` | 501 |
| `BulkActionToolbar` | 305 |
| `UploadProgressToast` | 86 |

### capture (2)

| Component | Lines |
| --- | ---: |
| `RTSPConnector` | 340 |
| `AudioMeter` | 69 |

### command-center (7)

| Component | Lines |
| --- | ---: |
| `IncidentDetailPanel` | 417 |
| `IncidentQueue` | 231 |
| `CommandCopilot` | 216 |
| `CommandTimeline` | 195 |
| `ShiftControl` | 163 |
| `CommandKPIs` | 142 |
| `VideoPanel` | 103 |

### copilot (1)

| Component | Lines |
| --- | ---: |
| `ProactiveCopilotBubble` | 56 |

### dashboard (1)

| Component | Lines |
| --- | ---: |
| `ModelHealthMonitor` | 101 |

### edge (7)

| Component | Lines |
| --- | ---: |
| `FormatOptionsPanel` | 326 |
| `InferenceBenchmark` | 308 |
| `ExportProgress` | 228 |
| `PackageGenerator` | 220 |
| `ModelSelector` | 170 |
| `LatencyHistogram` | 158 |
| `FormatComparisonTable` | 129 |

### evaluation (6)

| Component | Lines |
| --- | ---: |
| `BenchmarkForm` | 658 |
| `TournamentTab` | 370 |
| `BracketView` | 278 |
| `RadarChart` | 234 |
| `BenchmarkResults` | 223 |
| `BenchmarkHistory` | 195 |

### federated (7)

| Component | Lines |
| --- | ---: |
| `AccuracyLossChart` | 372 |
| `ContributionChart` | 329 |
| `PrivacyBudgetChart` | 221 |
| `RoundHistoryTable` | 218 |
| `FederationSelector` | 159 |
| `TrainingControls` | 140 |
| `index` | 3 |

### help (1)

| Component | Lines |
| --- | ---: |
| `HelpPanel` | 96 |

### investigate (6)

| Component | Lines |
| --- | ---: |
| `PlaybackTab` | 538 |
| `CommentsTab` | 533 |
| `ApprovalsTab` | 481 |
| `AddEvidenceModal` | 378 |
| `EvidenceTab` | 358 |
| `NewCaseModal` | 264 |

### knowledge-graph (7)

| Component | Lines |
| --- | ---: |
| `AddRelationshipModal` | 417 |
| `NodeDetailPanel` | 353 |
| `ExtractFromAsset` | 349 |
| `AddEntityModal` | 345 |
| `GraphSearch` | 216 |
| `CopilotGraphQuery` | 186 |
| `GraphExport` | 162 |

### marketplace (8)

| Component | Lines |
| --- | ---: |
| `BYOMTab` | 725 |
| `InstallModal` | 467 |
| `InstalledTab` | 415 |
| `PluginDetailPanel` | 405 |
| `PluginReviews` | 227 |
| `PluginConfigModal` | 176 |
| `FeaturedSection` | 87 |
| `PluginChangelog` | 80 |

### memory (8)

| Component | Lines |
| --- | ---: |
| `MemoryDetailPanel` | 786 |
| `MemoryNetworkGraph` | 533 |
| `DecayRulesModal` | 490 |
| `StoreMemoryModal` | 312 |
| `MemoryConflictsTab` | 311 |
| `MemoryCard` | 301 |
| `MemoryExplorer` | 260 |
| `index` | 2 |

### observability (5)

| Component | Lines |
| --- | ---: |
| `SLAHistoryChart` | 235 |
| `ErrorTaxonomyTable` | 232 |
| `PipelineHealthTable` | 223 |
| `RequestVolumeChart` | 205 |
| `SLABanner` | 127 |

### onboarding (5)

| Component | Lines |
| --- | ---: |
| `OnboardingWizard` | 106 |
| `WizardStep4` | 96 |
| `WizardStep3` | 87 |
| `WizardStep1` | 57 |
| `WizardStep2` | 45 |

### pipeline (4)

| Component | Lines |
| --- | ---: |
| `NodeConfigPanel` | 724 |
| `SavedPipelinesDrawer` | 332 |
| `GenerateModal` | 223 |
| `TemplatesModal` | 174 |

### reviewops (6)

| Component | Lines |
| --- | ---: |
| `ReviewWorkspace` | 744 |
| `TaskQueue` | 488 |
| `QualityTab` | 459 |
| `LeaderboardTab` | 328 |
| `ReviewStats` | 218 |
| `ConfusionMatrixHeatmap` | 196 |

### settings (20)

| Component | Lines |
| --- | ---: |
| `SecurityTab` | 693 |
| `GeneralTab` | 523 |
| `UsersTab` | 468 |
| `StorageTab` | 452 |
| `BillingTab` | 424 |
| `AuditLogTab` | 385 |
| `NotificationsTab` | 298 |
| `APIKeysTab` | 294 |
| `CreateAPIKeyModal` | 267 |
| `WebhookIntegration` | 239 |
| `IntegrationsTab` | 234 |
| `InviteUserModal` | 210 |
| `S3Integration` | 185 |
| `EmailIntegration` | 166 |
| `WebhookLogs` | 156 |
| `SlackIntegration` | 121 |
| `KeyRevealModal` | 89 |
| `SettingsNav` | 87 |
| `PlaceholderTabs` | 72 |
| `index` | 5 |

### shared (1)

| Component | Lines |
| --- | ---: |
| `ModuleCard` | 74 |

### simulation (4)

| Component | Lines |
| --- | ---: |
| `StressTestTab` | 536 |
| `EdgeCasesTab` | 535 |
| `SimulationReportsTab` | 485 |
| `ScenarioTemplates` | 363 |

### train (1)

| Component | Lines |
| --- | ---: |
| `index` | 4 |

### transform (1)

| Component | Lines |
| --- | ---: |
| `BeforeAfterSlider` | 113 |

### ui (6)

| Component | Lines |
| --- | ---: |
| `CommandPalette` | 285 |
| `ShortcutsModal` | 119 |
| `ErrorBoundary` | 65 |
| `OfflineBanner` | 55 |
| `HelpTooltip` | 42 |
| `PageStub` | 27 |

### verticals (5)

| Component | Lines |
| --- | ---: |
| `InstallModal` | 415 |
| `PackDetailPanel` | 391 |
| `InstalledPacksView` | 281 |
| `ManagePackModal` | 262 |
| `PackFilterBar` | 155 |

### vision (3)

| Component | Lines |
| --- | ---: |
| `DetectionOverlay` | 83 |
| `DualFrameUpload` | 18 |
| `SplitPaneLayout` | 17 |

## Second pass: imported, but never placed in the tree

The rule above - delete what nothing imports - is sound and it is not complete.
It cannot see a file that *is* imported by a page that then never renders it.
`AudioTransformStudio` was one; two more survived the first sweep for exactly
that reason:

| Component | Lines | Why it survived |
| --- | ---: | --- |
| `BatchTransformTab` | 560 | `transform/page.tsx` imported it with `dynamic()` |
| `PresetsTab` | 497 | `transform/page.tsx` imported it with `dynamic()` |

Both duplicated a tab the transform page already implements inline and renders -
the inline versions are the ones that have been running. 1,057 lines.

The guard test now covers this case too: an imported component binding that
appears in neither JSX nor any value position (a lookup table, an array, an
argument) cannot be rendered by any path, so it is reported the same way an
unimported file is.
