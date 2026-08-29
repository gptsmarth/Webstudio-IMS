import { useEffect, useState } from 'react';
import {
  ProductImageService,
  type ProductImageResult,
} from '../services/images/ProductImageService';

export interface UseProductImageOptions {
  remoteUrl?: string | null;
  brandName?: string | null;
  modelName?: string | null;
  category?: 'laptop' | 'generic';
}

export interface UseProductImageState {
  /** Always a usable <img> src — a real photo once found, a placeholder otherwise. */
  src: string;
  /** True only until the first resolve attempt returns (not while background-polling). */
  loading: boolean;
  /** True when there's no real photo yet (placeholder shown), including while pending. */
  failed: boolean;
  result: ProductImageResult | null;
}

const POLL_INTERVAL_MS = 5000;
// ~1 minute of polling — comfortably covers a background job that's queued behind the
// per-server concurrency cap (e.g. during a bulk import) as well as normal discovery time.
const MAX_POLL_ATTEMPTS = 12;

/**
 * Resolves a product's image and, if the backend reports discovery is still running in
 * the background ("pending"), keeps re-checking every few seconds so a newly-found photo
 * appears on its own — without the user needing to reload or navigate away and back.
 */
export function useProductImage(
  productModelId: string,
  options?: UseProductImageOptions,
): UseProductImageState {
  const { remoteUrl, brandName, modelName, category } = options ?? {};
  const [state, setState] = useState<UseProductImageState>({
    src: ProductImageService.getPlaceholderSrc(category),
    loading: true,
    failed: false,
    result: null,
  });

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    setState({
      src: ProductImageService.getPlaceholderSrc(category),
      loading: true,
      failed: false,
      result: null,
    });

    const runOnce = (isFirstAttempt: boolean) => {
      void ProductImageService.resolve(productModelId, {
        // Only the very first attempt should use the model's current stored URL — once we
        // know that came back pending, subsequent polls re-check discovery from scratch,
        // the same way ProductImagePanel's original retry logic did.
        remoteUrl: isFirstAttempt ? remoteUrl : null,
        brandName,
        modelName,
        category,
      }).then((result) => {
        if (cancelled) return;
        setState({
          src: result.src,
          loading: false,
          failed: result.source === 'placeholder' || result.source === 'pending',
          result,
        });
        if (result.source === 'pending' && attempts < MAX_POLL_ATTEMPTS) {
          attempts += 1;
          timer = setTimeout(() => runOnce(false), POLL_INTERVAL_MS);
        }
      });
    };

    runOnce(true);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [productModelId, remoteUrl, brandName, modelName, category]);

  return state;
}
