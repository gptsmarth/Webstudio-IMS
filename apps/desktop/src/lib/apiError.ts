interface ApiErrorBody {
  error?: { message?: string; code?: string };
  detail?: string;
  message?: string;
}

export function parseApiError(err: unknown, fallback = 'Request failed.'): string {
  const error = err as {
    response?: { data?: ApiErrorBody };
    message?: string;
  };
  const data = error.response?.data;
  if (data?.error?.message) return data.error.message;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.message === 'string') return data.message;
  return error.message ?? fallback;
}
