import type { SettingsWorkspaceState } from '../../hooks/useSettingsWorkspace';
import {
  AboutPanel,
  AppearancePanel,
  BackupPanel,
  DeploymentPanel,
  ExcelPanel,
  GeneralPanel,
  IntegrationsPanel,
  InventoryPanel,
  NotificationsPanel,
  SalesPanel,
  SecurityPanel,
  SystemPanel,
  TallyPanel,
} from './SettingsPanels';

interface SettingsCategoryPanelProps {
  workspace: SettingsWorkspaceState;
}

export function SettingsCategoryPanel({ workspace }: SettingsCategoryPanelProps): JSX.Element {
  const { category, workspace: data, locations } = workspace;

  if (!data) {
    return <p className="stg-loading">Loading settings…</p>;
  }

  const panelProps = { workspace, data, locations };

  switch (category) {
    case 'general':
      return <GeneralPanel {...panelProps} />;
    case 'security':
      return <SecurityPanel {...panelProps} />;
    case 'inventory':
      return <InventoryPanel {...panelProps} />;
    case 'sales':
      return <SalesPanel {...panelProps} />;
    case 'tally':
      return <TallyPanel {...panelProps} />;
    case 'integrations':
      return <IntegrationsPanel {...panelProps} />;
    case 'excel':
      return <ExcelPanel {...panelProps} />;
    case 'notifications':
      return <NotificationsPanel {...panelProps} />;
    case 'backup':
      return <BackupPanel {...panelProps} />;
    case 'deployment':
      return <DeploymentPanel />;
    case 'appearance':
      return <AppearancePanel />;
    case 'system':
      return <SystemPanel {...panelProps} />;
    case 'about':
      return <AboutPanel data={data} />;
    default:
      return <GeneralPanel {...panelProps} />;
  }
}
