import { describe, expect, it } from 'vitest';
import { useStockNavStore } from '../src/store/useHierarchyNavStore';

describe('hierarchy scroll persistence', () => {
  it('keeps scrollTops when returning from model to models list', () => {
    const store = useStockNavStore.getState();
    store.reset();
    store.setScrollTop('models-1', 420);
    store.openBrand(1, 'ASUS');
    store.openModel('m1', 'Model');
    expect(useStockNavStore.getState().level).toBe('serials');
    store.goToModels();
    expect(useStockNavStore.getState().level).toBe('models');
    expect(useStockNavStore.getState().getScrollTop('models-1')).toBe(420);
  });

  it('keeps scrollTops when returning to brands', () => {
    const store = useStockNavStore.getState();
    store.reset();
    store.setScrollTop('brands', 180);
    store.setScrollTop('models-1', 90);
    store.openBrand(1, 'ASUS');
    store.goToBrands();
    expect(useStockNavStore.getState().getScrollTop('brands')).toBe(180);
    expect(useStockNavStore.getState().getScrollTop('models-1')).toBe(90);
  });
});
