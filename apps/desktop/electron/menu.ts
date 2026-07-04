import { app, Menu, type MenuItemConstructorOptions } from 'electron';

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);

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

/**
 * macOS: Edit menu is always visible (platform convention).
 * Windows/Linux production: Edit menu is registered for Ctrl+C/V/X but the bar is auto-hidden (Alt to show).
 * Dev: Edit + View (DevTools).
 */
export function configureApplicationMenu(): void {
  if (process.platform === 'darwin') {
    const template: MenuItemConstructorOptions[] = [
      {
        label: app.name,
        submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
      },
      editMenu,
    ];

    if (isDev) {
      template.push({
        label: 'View',
        submenu: [{ role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' }],
      });
    }

    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
    return;
  }

  if (isDev) {
    Menu.setApplicationMenu(
      Menu.buildFromTemplate([
        editMenu,
        {
          label: 'View',
          submenu: [{ role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' }],
        },
      ]),
    );
    return;
  }

  // Windows/Linux production: Edit-only menu; window uses autoHideMenuBar (see main.ts).
  Menu.setApplicationMenu(Menu.buildFromTemplate([editMenu]));
}

/** Hide the menu bar on Windows/Linux production while keeping clipboard accelerators active. */
export function shouldAutoHideMenuBar(): boolean {
  return !isDev && process.platform !== 'darwin';
}
