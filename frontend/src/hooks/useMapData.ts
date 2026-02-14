import { useState, useEffect, useCallback, useRef } from "react";
import { getTractResults, TractResult } from "../services/api";

export interface TractFeature extends GeoJSON.Feature<GeoJSON.Geometry> {
  properties: Record<string, unknown>;
}

export interface TractGeoJSON extends GeoJSON.FeatureCollection<GeoJSON.Geometry> {
  features: TractFeature[];
}

const TRACTS_GEOJSON_URL = "/api/tracts/geojson";

export function useMapData(
  runId: string | null,
  timestep: number
) {
  const [baseGeoJSON, setBaseGeoJSON] = useState<TractGeoJSON | null>(null);
  const [mergedGeoJSON, setMergedGeoJSON] = useState<TractGeoJSON | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Fetch base tract geometries on mount
  useEffect(() => {
    const controller = new AbortController();
    fetch(TRACTS_GEOJSON_URL + "?_t=" + Date.now(), { signal: controller.signal })
      .then((res) => res.json())
      .then((data: TractGeoJSON) => {
        setBaseGeoJSON(data);
        setMergedGeoJSON(data);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Failed to load tract geometries:", err);
        }
      });
    return () => controller.abort();
  }, []);

  // Fetch and merge results when runId or timestep change
  const fetchAndMerge = useCallback(
    async (rid: string, ts: number) => {
      if (!baseGeoJSON) return;
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      try {
        const results: TractResult[] = await getTractResults(rid, ts);
        const resultMap = new Map<string, Record<string, number>>();
        for (const r of results) {
          resultMap.set(r.tract_id, r.properties);
        }

        const merged: TractGeoJSON = {
          type: "FeatureCollection",
          features: baseGeoJSON.features.map((f) => {
            const tractId = String(f.properties?.tract_id ?? f.properties?.GEOID ?? "");
            const resultProps = resultMap.get(tractId);
            return {
              ...f,
              properties: {
                ...f.properties,
                ...(resultProps ?? {}),
                _hasResult: !!resultProps,
              },
            };
          }),
        };
        if (!controller.signal.aborted) {
          setMergedGeoJSON(merged);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        console.error("Failed to fetch tract results:", err);
      } finally {
        setIsLoading(false);
      }
    },
    [baseGeoJSON]
  );

  useEffect(() => {
    if (runId) {
      fetchAndMerge(runId, timestep);
    } else if (baseGeoJSON) {
      setMergedGeoJSON(baseGeoJSON);
    }
  }, [runId, timestep, fetchAndMerge, baseGeoJSON]);

  return { geoJSON: mergedGeoJSON, isLoading };
}
