import { afterEach, describe, expect, it } from 'vitest';
import { _resetCategoriesForTest, AUDIO_CATEGORIES, categoryOf, getCategoryVolume, onCategoryChange, setCategoryVolume } from '../../src/audio/categories';
import { slideShape, MAX_LOOPS, LOOP_FAILSAFE_MS } from '../../src/audio/samples';

afterEach(() => _resetCategoriesForTest());

describe('audio categories', () => {
  it('routes every sample key family to one category', () => {
    expect(categoryOf('ui:click')).toBe('interface');
    expect(categoryOf('loading:done')).toBe('interface');
    for (const k of ['move:step:rime', 'step:heavy:emberhold', 'gallop:rime', 'slide:emberhold', 'slide:rime:stop', 'debris:rime:s2']) expect(categoryOf(k)).toBe('ambience');
    for (const k of ['hit:rook:emberhold', 'shatter:rime:heavy', 'shield:flash:rime', 'shield:break:emberhold', 'armour:hit:rime:heavy', 'land:emberhold:s3', 'check', 'mate', 'castle', 'sting:draw']) expect(categoryOf(k)).toBe('effects');
  });

  it('defaults to 1, clamps to 0..1, notifies listeners and survives missing localStorage', () => {
    for (const c of AUDIO_CATEGORIES) expect(getCategoryVolume(c)).toBe(1);
    const seen: Array<[string, number]> = [];
    const off = onCategoryChange((c, v) => seen.push([c, v]));
    setCategoryVolume('ambience', 0.25);
    setCategoryVolume('effects', 7);
    setCategoryVolume('music', -3);
    expect(getCategoryVolume('ambience')).toBe(0.25);
    expect(getCategoryVolume('effects')).toBe(1);
    expect(getCategoryVolume('music')).toBe(0);
    expect(seen).toEqual([['ambience', 0.25], ['effects', 1], ['music', 0]]);
    off();
    setCategoryVolume('interface', 0.5);
    expect(seen.length).toBe(3);
  });
});

describe('slide shaping', () => {
  it('pitch, gain and brightness rise monotonically with speed', () => {
    const a = slideShape(0.3); const b = slideShape(1.5); const c = slideShape(4);
    expect(a.rate).toBeLessThan(b.rate); expect(b.rate).toBeLessThan(c.rate);
    expect(a.gain).toBeLessThan(b.gain); expect(b.gain).toBeLessThan(c.gain);
    expect(a.cutoff).toBeLessThan(c.cutoff);
    expect(a.rate).toBeGreaterThan(0.7); expect(c.rate).toBeLessThanOrEqual(1.3);
    expect(slideShape(NaN).gain).toBeGreaterThan(0);
  });
  it('keeps the documented limits', () => {
    expect(MAX_LOOPS).toBe(2);
    expect(LOOP_FAILSAFE_MS).toBe(6000);
  });
});
