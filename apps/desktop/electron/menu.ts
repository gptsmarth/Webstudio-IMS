import { app, Menu, type MenuItemConstructorOptions } from 'electron';

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);

export interface ApplicationMenuHandlers {
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
}

/** Enables Cut/Copy/Paste/Select All — required for OS shortcuts in Electron text fields. */
const editMenu: MenuItemConstructorOptions = {
  label: 'Edit',
  submenu: [
    { role: 'undo' },
    { role: 'redo' },
    { type: 'separator' },
    { role: 'cut' },
    { role: 'copy' },
    { role: 'paste' },
    { role: 'selectAll' },
  ],
};

function viewMenu(handlers?: ApplicationMenuHandlers): MenuItemConstructorOptions {
  const zoomItems: MenuItemConstructorOptions[] = handlers
    ? [
        {
          label: 'Zoom In',
          accelerator: 'CmdOrCtrl+=',
          click: () => handlers.zoomIn(),
        },
        {
          label: 'Zoom In',
          accelerator: 'CmdOrCtrl+Plus',
          visible: false,
          acceleratorWorksWhenHidden: true,
          click: () => handlers.zoomIn(),
        },
        {
          label: 'Zoom Out',
          accelerator: 'CmdOrCtrl+-',
          click: () => handlers.zoomOut(),
        },
        {
          label: 'Actual Size',
          accelerator: 'CmdOrCtrl+0',
          click: () => handlers.resetZoom(),
        },
      ]
    : [];

  const submenu: MenuItemConstructorOptions[] = [
    ...zoomItems,
    ...(zoomItems.length > 0 && isDev ? [{ type: 'separator' as const }] : []),
    ...(isDev
      ? [
          { role: 'reload' as const },
          { role: 'forceReload' as const },
          { role: 'toggleDevTools' as const },
        ]
      : []),
  ];

  return {
    label: 'View',
    submenu:
      submenu.length > 0 ? submenu : [{ label: 'Zoom controls unavailable', enabled: false }],
  };
}

/**
 * macOS: Edit menu is always visible (platform convention).
 * Windows/Linux production: menu bar auto-hidden (Alt to show); accelerators still work.
 * Zoom shortcuts work even when the bar is hidden.
 */
export function configureApplicationMenu(handlers?: ApplicationMenuHandlers): void {
  if (process.platform === 'darwin') {
    const template: MenuItemConstructorOptions[] = [
      {
        label: app.name,
        submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
      },
      editMenu,
      viewMenu(handlers),
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
    return;
  }

  Menu.setApplicationMenu(Menu.buildFromTemplate([editMenu, viewMenu(handlers)]));
}

/** Hide the menu bar on Windows/Linux production while keeping clipboard/zoom accelerators active. */
export function shouldAutoHideMenuBar(): boolean {
  return !isDev && process.platform !== 'darwin';
}
