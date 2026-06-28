import { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import { ProductImageService, type ProductImageResult } from '../../services/images/ProductImageService';

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
    void ProductImageService.resolve(productModelId, { remoteUrl: imageUrl }).then((result) => {
      if (!cancelled) setImage(result);
    });
    return () => {
      cancelled = true;
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

  return (
    <div className="inv-product-image">
      <div className="inv-product-image__frame">
        {image ? (
          <img src={image.src} alt={modelName} className="inv-product-image__img" />
        ) : (
          <div className="skeleton inv-product-image__skeleton" />
        )}
      </div>
      {readOnly ? (
        <p className="inv-product-image__hint">
          Inherited from the product model. Images can be set when adding laptops in Inventory.
        </p>
      ) : (
        <>
          <label className="btn btn-secondary btn-sm inv-product-image__upload">
            <Upload size={14} aria-hidden />
            {uploading ? 'Uploading…' : 'Upload image'}
            <input type="file" accept="image/*" className="inv-product-image__file" onChange={(event) => void onUpload(event)} />
          </label>
          <p className="inv-product-image__hint">Local cache only. Remote fetching will be enabled in a future release.</p>
        </>
      )}
    </div>
  );
}
