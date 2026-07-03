import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  buildReportQueryParams,
  DEFAULT_REPORT_FILTERS,
  type ReportBuilderFilters,
} from '../lib/reportBuilder';
import { BrandService, type Brand } from '../services/api/BrandService';
import { LocationService, type Location } from '../services/api/LocationService';
import { ProductModelService, type ProductModel } from '../services/api/ProductModelService';
import {
  ReportService,
  type AuditReportRow,
  type BuilderReportType,
  type ExportFormat,
  type InventoryReportRow,
  type NotificationReportRow,
  type SalesReportRow,
} from '../services/api/ReportService';

export type { ReportBuilderFilters };
export { DEFAULT_REPORT_FILTERS };

export type PreviewRow =
  | InventoryReportRow
  | SalesReportRow
  | AuditReportRow
  | NotificationReportRow;

export function useReportBuilder() {
  const [reportType, setReportType] = useState<BuilderReportType>('inventory');
  const [filters, setFiltersState] = useState<ReportBuilderFilters>(DEFAULT_REPORT_FILTERS);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [productModels, setProductModels] = useState<ProductModel[]>([]);
  const [rows, setRows] = useState<PreviewRow[]>([]);
  const [summary, setSummary] = useState<{
    total_rows: number;
    by_status: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [hasPreviewed, setHasPreviewed] = useState(false);
  const hasPreviewedRef = useRef(false);

  useEffect(() => {
    hasPreviewedRef.current = hasPreviewed;
  }, [hasPreviewed]);

  const setFilters = useCallback((patch: Partial<ReportBuilderFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
    setHasPreviewed(false);
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_REPORT_FILTERS);
    setHasPreviewed(false);
    setPage(1);
    setSortField(null);
    setSortDirection('desc');
  }, []);

  const changeReportType = useCallback((next: BuilderReportType) => {
    setReportType(next);
    setFiltersState(DEFAULT_REPORT_FILTERS);
    setRows([]);
    setSummary(null);
    setHasPreviewed(false);
    setPage(1);
    setError(null);
    setSortField(null);
    setSortDirection('desc');
  }, []);

  const queryParams = useMemo(
    () => buildReportQueryParams(reportType, filters, page, pageSize, sortField, sortDirection),
    [reportType, filters, page, pageSize, sortField, sortDirection],
  );

  const runPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await ReportService.preview<PreviewRow>(reportType, queryParams);
      setRows(result.rows);
      setSummary(result.summary ?? null);
      setTotalItems(result.total_items);
      setTotalPages(result.total_pages);
      setHasPreviewed(true);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load report preview.');
      setRows([]);
      setSummary(null);
      setTotalItems(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [queryParams, reportType]);

  const exportReport = useCallback(
    async (format: ExportFormat) => {
      if (!hasPreviewed) return;
      setExporting(true);
      setError(null);
      try {
        await ReportService.exportReport(reportType, format, queryParams);
      } catch (err: unknown) {
        const message = err as { message?: string };
        setError(message.message ?? 'Export failed.');
      } finally {
        setExporting(false);
      }
    },
    [hasPreviewed, queryParams, reportType],
  );

  const toggleSort = useCallback((field: string) => {
    setSortField((current) => {
      if (current === field) {
        setSortDirection((dir) => (dir === 'asc' ? 'desc' : 'asc'));
        return field;
      }
      setSortDirection('asc');
      return field;
    });
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [brandList, locationList] = await Promise.all([
          BrandService.listBrands(),
          LocationService.listLocations(),
        ]);
        setBrands(brandList);
        setLocations(locationList);
      } catch {
        // Reference data optional for page shell
      }
    })();
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const models = await ProductModelService.listModels(filters.brandId ?? undefined);
        setProductModels(models);
      } catch {
        setProductModels([]);
      }
    })();
  }, [filters.brandId]);

  useEffect(() => {
    if (!hasPreviewedRef.current) return;
    void runPreview();
  }, [page, sortField, sortDirection, runPreview]);

  return {
    reportType,
    changeReportType,
    filters,
    setFilters,
    resetFilters,
    brands,
    locations,
    productModels,
    rows,
    summary,
    loading,
    exporting,
    error,
    page,
    pageSize,
    totalItems,
    totalPages,
    setPage,
    sortField,
    sortDirection,
    toggleSort,
    runPreview,
    exportReport,
    hasPreviewed,
  };
}
