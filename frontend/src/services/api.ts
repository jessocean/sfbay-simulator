import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export interface PolicyConfig {
  [key: string]: unknown;
}

export interface ParseResponse {
  config: PolicyConfig;
  summary: string;
  affected_tracts: string[];
  warnings?: string[];
}

export interface RefineResponse extends ParseResponse {}

export interface PredefinedScenario {
  id: string;
  name: string;
  description: string;
  config: PolicyConfig;
}

export interface RunSimulationResponse {
  run_id: string;
}

export interface SimulationStatus {
  run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_step: number;
  total_steps: number;
  message?: string;
}

export interface TractResult {
  tract_id: string;
  geometry: GeoJSON.Geometry;
  properties: Record<string, number>;
}

export interface MetricsResult {
  [metric: string]: {
    current: number;
    baseline: number;
    delta: number;
    delta_pct: number;
  };
}

export interface TimeseriesPoint {
  timestep: number;
  date: string;
  value: number;
}

export async function parsePolicy(text: string): Promise<ParseResponse> {
  const res = await client.post("/parse", { text });
  return res.data;
}

export async function refinePolicy(
  text: string,
  config: PolicyConfig
): Promise<RefineResponse> {
  const res = await client.post("/parse/refine", { text, current_config: config });
  return res.data;
}

export async function getPredefinedScenarios(): Promise<PredefinedScenario[]> {
  const res = await client.get("/scenarios/predefined");
  return res.data;
}

export async function runSimulation(
  config: PolicyConfig
): Promise<RunSimulationResponse> {
  const res = await client.post("/simulations/run", { config });
  return res.data;
}

export async function getSimulationStatus(
  runId: string
): Promise<SimulationStatus> {
  const res = await client.get(`/simulations/status/${runId}`);
  return res.data;
}

export async function getTractResults(
  runId: string,
  timestep: number
): Promise<TractResult[]> {
  const res = await client.get(`/results/${runId}/tracts`, {
    params: { timestep },
  });
  return res.data;
}

export async function getMetrics(
  runId: string,
  timestep: number
): Promise<MetricsResult> {
  const res = await client.get(`/results/${runId}/metrics`, {
    params: { timestep },
  });
  return res.data;
}

export async function getTimeseries(
  runId: string,
  metric: string
): Promise<TimeseriesPoint[]> {
  const res = await client.get(`/results/${runId}/timeseries`, {
    params: { metric },
  });
  return res.data;
}
