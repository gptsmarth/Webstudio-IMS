export class LoggingService {
  private static async dispatch(
    channel: LogChannel,
    level: LogLevel,
    message: string,
    meta?: Record<string, unknown>,
  ): Promise<void> {
    const formatted = `[${channel}] [${level.toUpperCase()}] ${message}`;

    if (level === 'error') {
      console.error(formatted, meta ?? '');
    } else if (level === 'warn') {
      console.warn(formatted, meta ?? '');
    } else {
      console.log(formatted, meta ?? '');
    }

    try {
      if (typeof window !== 'undefined' && window.system?.log) {
        await window.system.log(channel, level, message, meta);
      }
    } catch {
      // Ignore IPC logging errors
    }
  }

  static debug(channel: LogChannel, message: string, meta?: Record<string, unknown>): void {
    void this.dispatch(channel, 'debug', message, meta);
  }

  static info(channel: LogChannel, message: string, meta?: Record<string, unknown>): void {
    void this.dispatch(channel, 'info', message, meta);
  }

  static warn(channel: LogChannel, message: string, meta?: Record<string, unknown>): void {
    void this.dispatch(channel, 'warn', message, meta);
  }

  static error(channel: LogChannel, message: string, meta?: Record<string, unknown>): void {
    void this.dispatch(channel, 'error', message, meta);
  }
}
