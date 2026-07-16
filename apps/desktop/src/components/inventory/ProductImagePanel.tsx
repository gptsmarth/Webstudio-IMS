import { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import {
  ProductImageService,
  type ProductImageResult,
} from '../../services/images/ProductImageService';

interface ProductImagePanelProps {
  productModelId: string;
  modelName: string;
  /** HTTPS product image URL (e.g. from Gemini) used when no local cache exists. */
  imageUrl?: string | null;
  /** When true, image is read-only and inherited from the product model. */
  readOnly?: boolean;
}

export function ProductImagePanel({
  productModelId,
  modelName,
  imageUrl,
  readOnly = false,
}: ProductImagePanelProps): JSX.Element {
  const [image, setImage] = useState<ProductImageResult | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    const apply = (result: ProductImageResult) => {
      if (!cancelled) setImage(result);
    };

    void ProductImageService.resolve(productModelId, { remoteUrl: imageUrl }).then((result) => {
      apply(result);
      // If the model has no image yet, background discovery may finish shortly —
      // re-check a couple of times without blocking the add flow.
      if (!imageUrl?.trim() && result.source === 'placeholder') {
        pollTimer = setTimeout(() => {
          if (cancelled) return;
          void ProductImageService.resolve(productModelId, { remoteUrl: null }).then((again) => {
            apply(again);
            if (again.source === 'placeholder' && !cancelled) {
              pollTimer = setTimeout(() => {
                if (cancelled) return;
                void ProductImageService.resolve(productModelId, { remoteUrl: null }).then(apply);
              }, 12_000);
            }
          });
        }, 6_000);
      }
    });

    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [productModelId, imageUrl]);

  const onUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (readOnly) return;
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await ProductImageService.uploadFromFile(productModelId, file);
      setImage(result);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const placeholderSrc = ProductImageService.getPlaceholderSrc();

  return (
    <div className="inv-product-image">
      <div className="inv-product-image__frame">
        {image ? (
          <img
            src={image.src}
            alt={modelName}
            className="inv-product-image__img"
            onError={(event) => {
              event.currentTarget.onerror = null;
              event.currentTarget.src = placeholderSrc;
            }}
          />
        ) : (
          <div className="skeleton inv-product-image__skeleton" />
        )}
      </div>
      {readOnly ? (
        <p className="inv-product-image__hint">
          Inherited from the product model. Images are fetched in the background after a model is
          added, or you can upload one from Inventory.
        </p>
      ) : (
        <>
          <label className="btn btn-secondary btn-sm inv-product-image__upload">
            <Upload size={14} aria-hidden />
            {uploading ? 'Uploading…' : 'Upload image'}
            <input
              type="file"
              accept="image/*"
              className="inv-product-image__file"
              onChange={(event) => void onUpload(event)}
            />
          </label>
          <p className="inv-product-image__hint">
            Upload a photo, or leave blank — the server fetches images in the background.
          </p>
        </>
      )}
    </div>
  );
}
