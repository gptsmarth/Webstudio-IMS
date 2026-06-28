import type { WorkspaceRoute } from '../../config/navigation';
import { useNavigationStore } from '../../store';
import { PageBackButton } from './PageBackButton';

interface WorkspacePageBackProps {
  fallbackRoute?: WorkspaceRoute;
  label?: string;
}

export function WorkspacePageBack({
  fallbackRoute = 'dashboard',
  label = 'Back to Dashboard',
}: WorkspacePageBackProps): JSX.Element {
  const setRoute = useNavigationStore((state) => state.setRoute);
  return <PageBackButton label={label} onClick={() => setRoute(fallbackRoute)} />;
}
