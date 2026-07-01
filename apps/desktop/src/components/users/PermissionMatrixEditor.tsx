import { buildPermissionModules } from '../../lib/userPermissions';

interface PermissionMatrixEditorProps {
  catalog: string[];
  selected: string[];
  onChange: (permissions: string[]) => void;
}

export function PermissionMatrixEditor({
  catalog,
  selected,
  onChange,
}: PermissionMatrixEditorProps): JSX.Element {
  const modules = buildPermissionModules(catalog, { roleLabel: 'Custom role' });
  const selectedSet = new Set(selected);
  const catalogSet = new Set(catalog);
  const allCatalogSelected = catalog.every((permission) => selectedSet.has(permission));

  const applySelection = (next: Set<string>) => {
    onChange([...next].filter((permission) => catalogSet.has(permission)).sort());
  };

  const toggle = (permission: string) => {
    const next = new Set(selectedSet);
    if (next.has(permission)) next.delete(permission);
    else next.add(permission);
    applySelection(next);
  };

  const toggleModule = (permissions: string[]) => {
    const next = new Set(selectedSet);
    const allSelected = permissions.every((permission) => next.has(permission));
    for (const permission of permissions) {
      if (allSelected) next.delete(permission);
      else next.add(permission);
    }
    applySelection(next);
  };

  const toggleAll = () => {
    if (allCatalogSelected) {
      applySelection(new Set());
    } else {
      applySelection(new Set(catalog));
    }
  };

  return (
    <div className="usr-permission-matrix">
      <div className="usr-permission-matrix__toolbar">
        <p className="usr-permission-matrix__hint">
          Choose which app sections this role can access. Dashboard permissions control individual widgets on the operations center.
        </p>
        <button type="button" className="btn btn-ghost btn-sm" onClick={toggleAll}>
          {allCatalogSelected ? 'Clear all' : 'Select all'}
        </button>
      </div>
      <div className="usr-permission-matrix__modules">
        {modules.map((module) => {
          const moduleCapabilities = module.capabilities.filter((capability) => (
            catalog.includes(capability.permission)
          ));
          if (moduleCapabilities.length === 0) return null;
          const modulePermissions = moduleCapabilities.map((capability) => capability.permission);
          const moduleAllSelected = modulePermissions.every((permission) => selectedSet.has(permission));
          return (
            <section key={module.moduleId} className="usr-permission-matrix__module">
              <div className="usr-permission-matrix__module-head">
                <h3 className="usr-permission-matrix__module-title">{module.module}</h3>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm usr-permission-matrix__module-select"
                  onClick={() => toggleModule(modulePermissions)}
                >
                  {moduleAllSelected ? 'Clear section' : 'Select section'}
                </button>
              </div>
              <ul className="usr-permission-matrix__list">
                {moduleCapabilities.map((capability) => {
                  const checked = selectedSet.has(capability.permission);
                  return (
                    <li key={capability.permission}>
                      <button
                        type="button"
                        className={`usr-permission-matrix__row${checked ? ' usr-permission-matrix__row--checked' : ''}`}
                        onClick={() => toggle(capability.permission)}
                        aria-pressed={checked}
                      >
                        <span className="usr-permission-matrix__checkbox" aria-hidden>
                          {checked ? '✓' : ''}
                        </span>
                        <span className="usr-permission-matrix__row-body">
                          <span className="usr-permission-matrix__row-label">{capability.label}</span>
                          <span className="usr-permission-matrix__row-desc">{capability.description}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
