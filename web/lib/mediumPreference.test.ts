import { beforeEach, describe, expect, it } from "vitest";
import { readMediumPreference, writeMediumPreference } from "./mediumPreference";

// No jsdom in this harness (vitest.config.mts scopes tests to pure lib/
// logic in a plain node environment - see its own comment on why) - a
// minimal in-memory stub is enough to exercise the real read/write
// paths without pulling in a browser DOM dependency for one module.
function makeLocalStorageStub(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => store.clear(),
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  };
}

describe("mediumPreference", () => {
  beforeEach(() => {
    (globalThis as { localStorage: Storage }).localStorage = makeLocalStorageStub();
  });

  it("returns null when nothing has been written yet", () => {
    expect(readMediumPreference()).toBeNull();
  });

  it("round-trips a written medium", () => {
    writeMediumPreference("music");
    expect(readMediumPreference()).toBe("music");

    writeMediumPreference("webtoons");
    expect(readMediumPreference()).toBe("webtoons");
  });

  it("ignores a garbage value some other code path may have left behind", () => {
    localStorage.setItem("aura-last-medium", "not-a-real-medium");
    expect(readMediumPreference()).toBeNull();
  });
});
