import { useEffect, useState } from "react";
import { fetchCompanies } from "@/lib/api";

export interface CompanyEntry {
  display: string;
  careersUrl: string | null;
}

export type CompanyMap = Map<string, CompanyEntry>;

export function formatCompanyName(raw: string): string {
  if (!raw) return raw;
  if (/[A-Z]/.test(raw)) return raw;
  return raw.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function useCompanyMap(): CompanyMap {
  const [map, setMap] = useState<CompanyMap>(() => new Map());

  useEffect(() => {
    let cancelled = false;
    fetchCompanies()
      .then((rows) => {
        if (cancelled) return;
        const next: CompanyMap = new Map();
        for (const row of rows) {
          next.set(row.name.toLowerCase(), {
            display: formatCompanyName(row.name),
            careersUrl: row.careers_url,
          });
        }
        setMap(next);
      })
      .catch((e) => console.error("fetchCompanies failed", e));
    return () => {
      cancelled = true;
    };
  }, []);

  return map;
}

export function lookupCompany(map: CompanyMap, raw: string): CompanyEntry {
  const hit = map.get(raw.toLowerCase());
  return {
    display: hit?.display ?? formatCompanyName(raw),
    careersUrl: hit?.careersUrl ?? null,
  };
}
