import { app, Menu, type MenuItemConstructorOptions } from 'electron';

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);

/**
 * Production desktop builds should not show the default Electron File/Edit/View menu.
 * Dev builds keep a minimal menu with DevTools for debugging.
 */
export function configureApplicationMenu(): void {
  if (process.platform === 'darwin') {
    const template: MenuItemConstructorOptions[] = [
      {
        label: app.name,
        submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
      },
    ];

    if (isDev) {
      template.push({
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
        ],
      });
    }

    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
    return;
  }

  if (isDev) {
    Menu.setApplicationMenu(
      Menu.buildFromTemplate([
        {
          label: 'View',
          submenu: [
            { role: 'reload' },
            { role: 'forceReload' },
            { role: 'toggleDevTools' },
          ],
        },
      ]),
    );
    return;
  }

  Menu.setApplicationMenu(null);
}
