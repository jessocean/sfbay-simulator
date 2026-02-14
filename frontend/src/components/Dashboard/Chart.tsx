import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { Box, Typography } from "@mui/material";
import type { TimeseriesPoint } from "../../services/api";

interface ChartProps {
  data: TimeseriesPoint[];
  metric: string;
  currentTimestep: number;
}

const Chart: React.FC<ChartProps> = ({ data, metric, currentTimestep }) => {
  if (!data || data.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: "center" }}>
        <Typography variant="caption" color="text.secondary">
          No timeseries data available
        </Typography>
      </Box>
    );
  }

  const formatLabel = (name: string): string =>
    name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <Box sx={{ width: "100%", height: 180 }}>
      <Typography variant="caption" color="text.secondary" sx={{ pl: 1 }}>
        {formatLabel(metric)} over time
      </Typography>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#888" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#888" }}
            width={55}
            tickFormatter={(v: number) =>
              v >= 1000000
                ? `${(v / 1000000).toFixed(1)}M`
                : v >= 1000
                ? `${(v / 1000).toFixed(1)}K`
                : v.toFixed(1)
            }
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e1e2e",
              border: "1px solid #444",
              borderRadius: 4,
              fontSize: 12,
            }}
            labelStyle={{ color: "#aaa" }}
          />
          <ReferenceLine
            x={data[currentTimestep]?.date}
            stroke="#ff9800"
            strokeWidth={2}
            strokeDasharray="4 2"
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#42a5f5"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default Chart;
