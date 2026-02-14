import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  MenuItem,
  Select,
  Paper,
  FormControl,
  InputLabel,
  SelectChangeEvent,
} from "@mui/material";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import { getMetrics, getTimeseries, MetricsResult, TimeseriesPoint } from "../../services/api";
import Chart from "./Chart";

const AVAILABLE_METRICS = [
  { key: "population", label: "Population" },
  { key: "median_rent", label: "Median Rent" },
  { key: "housing_units", label: "Housing Units" },
  { key: "transit_share", label: "Transit Share" },
  { key: "crime", label: "Crime" },
  { key: "vacancy", label: "Vacancy" },
  { key: "businesses", label: "Businesses" },
  { key: "drug_market_activity", label: "Drug Market Activity" },
];

interface MetricsPanelProps {
  runId: string | null;
  currentTimestep: number;
  selectedMetric: string;
  onMetricChange: (metric: string) => void;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({
  runId,
  currentTimestep,
  selectedMetric,
  onMetricChange,
}) => {
  const [metrics, setMetrics] = useState<MetricsResult | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);

  useEffect(() => {
    if (!runId) {
      setMetrics(null);
      return;
    }
    getMetrics(runId, currentTimestep)
      .then(setMetrics)
      .catch(() => setMetrics(null));
  }, [runId, currentTimestep]);

  useEffect(() => {
    if (!runId) {
      setTimeseries([]);
      return;
    }
    getTimeseries(runId, selectedMetric)
      .then(setTimeseries)
      .catch(() => setTimeseries([]));
  }, [runId, selectedMetric]);

  const handleChange = (e: SelectChangeEvent) => {
    onMetricChange(e.target.value);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, p: 2 }}>
      <Typography variant="subtitle2" fontWeight={700}>
        Metrics Dashboard
      </Typography>

      <FormControl size="small" fullWidth>
        <InputLabel>Metric</InputLabel>
        <Select value={selectedMetric} onChange={handleChange} label="Metric">
          {AVAILABLE_METRICS.map((m) => (
            <MenuItem key={m.key} value={m.key}>
              {m.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Metric cards */}
      {metrics && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 1,
          }}
        >
          {AVAILABLE_METRICS.map(({ key, label }) => {
            const m = metrics[key];
            if (!m) return null;
            const isPositive = m.delta >= 0;
            return (
              <Paper
                key={key}
                variant="outlined"
                sx={{
                  p: 1,
                  bgcolor:
                    key === selectedMetric
                      ? "action.selected"
                      : "background.default",
                  cursor: "pointer",
                  "&:hover": { bgcolor: "action.hover" },
                  transition: "background-color 0.2s",
                }}
                onClick={() => onMetricChange(key)}
              >
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ fontSize: "0.65rem", lineHeight: 1.2, display: "block" }}
                >
                  {label}
                </Typography>
                <Typography variant="body2" fontWeight={700} sx={{ lineHeight: 1.3 }}>
                  {m.current >= 1000000
                    ? `${(m.current / 1000000).toFixed(2)}M`
                    : m.current >= 1000
                    ? `${(m.current / 1000).toFixed(1)}K`
                    : m.current.toFixed(1)}
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.3,
                    mt: 0.2,
                  }}
                >
                  {isPositive ? (
                    <ArrowUpwardIcon
                      sx={{ fontSize: 12, color: "success.main" }}
                    />
                  ) : (
                    <ArrowDownwardIcon
                      sx={{ fontSize: 12, color: "error.main" }}
                    />
                  )}
                  <Typography
                    variant="caption"
                    sx={{
                      fontSize: "0.65rem",
                      color: isPositive ? "success.main" : "error.main",
                    }}
                  >
                    {isPositive ? "+" : ""}
                    {m.delta_pct.toFixed(1)}%
                  </Typography>
                </Box>
              </Paper>
            );
          })}
        </Box>
      )}

      {!runId && (
        <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center", py: 2 }}>
          Run a simulation to see metrics
        </Typography>
      )}

      {/* Timeseries chart */}
      {runId && timeseries.length > 0 && (
        <Chart
          data={timeseries}
          metric={selectedMetric}
          currentTimestep={currentTimestep}
        />
      )}
    </Box>
  );
};

export default MetricsPanel;
