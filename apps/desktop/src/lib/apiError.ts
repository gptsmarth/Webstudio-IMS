interface ApiErrorDetail {
  field?: string;
  message?: string;
}

interface ApiErrorBody {
  error?: {
    message?: string;
    code?: string;
    details?: ApiErrorDetail[];
  };
  detail?: string | ApiErrorDetail[];
  message?: string;
}

export function parseApiError(err: unknown, fallback = 'Request failed.'): string {
  const error = err as {
    response?: { data?: ApiErrorBody };
    message?: string;
  };
  const data = error.response?.data;
  const details = data?.error?.details;
  if (details && details.length > 0) {
    const parts = details
      .map((entry) => {
        const field = entry.field?.trim();
        const message = entry.message?.trim();
        if (!message) return null;
        return field ? `${field}: ${message}` : message;
      })
      .filter((entry): entry is string => Boolean(entry));
    if (parts.length > 0) {
      const base = data?.error?.message ?? 'Request validation failed.';
      return `${base} ${parts.join(' ')}`;
    }
  }
  if (data?.error?.message) return data.error.message;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.message === 'string') return data.message;
  return error.message ?? fallback;
}
