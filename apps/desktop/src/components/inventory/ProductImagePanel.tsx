import { useState } from 'react';
import { Upload } from 'lucide-react';
import { ProductImageService } from '../../services/images/ProductImageService';
import { useProductImage } from '../../hooks/useProductImage';

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
  const [uploading, setUploading] = useState(false);
  const [uploadedOverride, setUploadedOverride] = useState<{ id: string; src: string } | null>(
    null,
  );
  // Background discovery may still be running when this panel first mounts (e.g. right
  // after adding a product) — useProductImage keeps re-checking until it finishes.
  const image = useProductImage(productModelId, { remoteUrl: imageUrl });
  const displaySrc =
    uploadedOverride?.id === productModelId
      ? uploadedOverride.src
      : image.loading
        ? null
        : image.src;

  const onUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (readOnly) return;
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await ProductImageService.uploadFromFile(productModelId, file);
      setUploadedOverride({ id: productModelId, src: result.src });
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const placeholderSrc = ProductImageService.getPlaceholderSrc();

  return (
    <div className="inv-product-image">
      <div className="inv-product-image__frame">
        {displaySrc ? (
          <img
            src={displaySrc}
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
