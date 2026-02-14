import { GeoJsonLayer } from "@deck.gl/layers";
import { scaleSequential } from "d3-scale";
import { interpolateRdYlBu } from "d3-scale-chromatic";
import type { TractGeoJSON } from "../../hooks/useMapData";

function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return [100, 100, 100];
  return [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16),
  ];
}

export interface TractLayerProps {
  data: TractGeoJSON | null;
  selectedMetric: string;
  affectedTracts: string[];
  highlightAffected: boolean;
  onTractClick?: (info: { tract_id: string; properties: Record<string, unknown>; coordinate: [number, number] }) => void;
}

export function createTractLayer({
  data,
  selectedMetric,
  affectedTracts,
  highlightAffected,
  onTractClick,
}: TractLayerProps): GeoJsonLayer | null {
  if (!data) return null;

  // Compute min/max for the selected metric across all features
  const values: number[] = [];
  for (const f of data.features) {
    const val = f.properties?.[selectedMetric];
    if (typeof val === "number" && isFinite(val)) {
      values.push(val);
    }
  }

  const minVal = values.length > 0 ? Math.min(...values) : 0;
  const maxVal = values.length > 0 ? Math.max(...values) : 1;

  // Reversed so blue = low, red = high
  const colorScale = scaleSequential(interpolateRdYlBu).domain([maxVal, minVal]);

  const affectedSet = new Set(affectedTracts);

  return new GeoJsonLayer({
    id: "tract-layer",
    data: data as unknown as GeoJSON.FeatureCollection,
    filled: true,
    stroked: true,
    pickable: true,
    extruded: false,
    lineWidthMinPixels: 0.5,
    getFillColor: (f: GeoJSON.Feature) => {
      const props = f.properties as Record<string, unknown> | null;
      const val = props?.[selectedMetric];
      if (typeof val === "number" && isFinite(val)) {
        const hex = colorScale(val);
        const [r, g, b] = hexToRgb(hex);
        return [r, g, b, 180] as [number, number, number, number];
      }
      return [40, 40, 50, 120] as [number, number, number, number];
    },
    getLineColor: (f: GeoJSON.Feature) => {
      const props = f.properties as Record<string, unknown> | null;
      const tractId = String(props?.tract_id ?? props?.GEOID ?? "");
      if (highlightAffected && affectedSet.has(tractId)) {
        return [0, 255, 200, 255] as [number, number, number, number];
      }
      return [60, 60, 70, 100] as [number, number, number, number];
    },
    getLineWidth: (f: GeoJSON.Feature) => {
      const props = f.properties as Record<string, unknown> | null;
      const tractId = String(props?.tract_id ?? props?.GEOID ?? "");
      if (highlightAffected && affectedSet.has(tractId)) {
        return 3;
      }
      return 0.5;
    },
    updateTriggers: {
      getFillColor: [selectedMetric, minVal, maxVal],
      getLineColor: [affectedTracts, highlightAffected],
      getLineWidth: [affectedTracts, highlightAffected],
    },
    transitions: {
      getFillColor: { duration: 300 },
    },
    onClick: (info: { object?: GeoJSON.Feature; coordinate?: number[] }) => {
      if (info.object && onTractClick) {
        const props = (info.object.properties ?? {}) as Record<string, unknown>;
        const tractId = String(props.tract_id ?? props.GEOID ?? "");
        onTractClick({
          tract_id: tractId,
          properties: props,
          coordinate: (info.coordinate as [number, number]) ?? [0, 0],
        });
      }
    },
  });
}
