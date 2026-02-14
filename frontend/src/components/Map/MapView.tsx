import React, { useState, useCallback } from "react";
import Map from "react-map-gl/maplibre";
import DeckGL from "@deck.gl/react";
import { Box, Paper, Typography, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { createTractLayer } from "./TractLayer";
import type { TractGeoJSON } from "../../hooks/useMapData";

const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const INITIAL_VIEW_STATE = {
  latitude: 37.56,
  longitude: -122.15,
  zoom: 9,
  pitch: 0,
  bearing: 0,
};

interface PopupInfo {
  tract_id: string;
  properties: Record<string, unknown>;
  coordinate: [number, number];
}

interface MapViewProps {
  geoJSON: TractGeoJSON | null;
  selectedMetric: string;
  affectedTracts: string[];
  highlightAffected: boolean;
}

const MapView: React.FC<MapViewProps> = ({
  geoJSON,
  selectedMetric,
  affectedTracts,
  highlightAffected,
}) => {
  const [popup, setPopup] = useState<PopupInfo | null>(null);
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);

  const handleTractClick = useCallback(
    (info: {
      tract_id: string;
      properties: Record<string, unknown>;
      coordinate: [number, number];
    }) => {
      setPopup(info);
    },
    []
  );

  const layer = createTractLayer({
    data: geoJSON,
    selectedMetric,
    affectedTracts,
    highlightAffected,
    onTractClick: handleTractClick,
  });

  const layers = layer ? [layer] : [];

  return (
    <Box sx={{ position: "relative", width: "100%", height: "100%" }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs as typeof viewState)}
        controller={true}
        layers={layers}
        getTooltip={({ object }: { object?: GeoJSON.Feature }) => {
          if (!object) return null;
          const props = object.properties as Record<string, unknown> | null;
          const tractId = props?.tract_id ?? props?.GEOID ?? "Unknown";
          const metricVal = props?.[selectedMetric];
          return {
            text: `Tract: ${tractId}\n${selectedMetric}: ${
              typeof metricVal === "number" ? metricVal.toLocaleString() : "N/A"
            }`,
            style: {
              backgroundColor: "#1e1e2e",
              color: "#fff",
              fontSize: "12px",
              padding: "6px 10px",
              borderRadius: "4px",
            },
          };
        }}
      >
        <Map mapStyle={MAP_STYLE} />
      </DeckGL>

      {popup && (
        <Paper
          elevation={6}
          sx={{
            position: "absolute",
            top: 16,
            right: 16,
            width: 280,
            p: 2,
            bgcolor: "background.paper",
            borderRadius: 2,
            zIndex: 10,
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography variant="subtitle1" fontWeight={700}>
              Tract {popup.tract_id}
            </Typography>
            <IconButton size="small" onClick={() => setPopup(null)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ maxHeight: 300, overflowY: "auto" }}>
            {Object.entries(popup.properties)
              .filter(([key]) => !key.startsWith("_") && key !== "tract_id" && key !== "GEOID")
              .map(([key, value]) => (
                <Box
                  key={key}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    py: 0.3,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {key}
                  </Typography>
                  <Typography variant="caption" fontWeight={600}>
                    {typeof value === "number"
                      ? value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })
                      : String(value ?? "")}
                  </Typography>
                </Box>
              ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default MapView;
