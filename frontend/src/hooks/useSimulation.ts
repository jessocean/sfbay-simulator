import { useState, useCallback, useRef } from "react";
import {
  PolicyConfig,
  ParseResponse,
  SimulationStatus,
  parsePolicy as apiParsePolicy,
  refinePolicy as apiRefinePolicy,
  runSimulation as apiRunSimulation,
  getSimulationStatus,
} from "../services/api";

export interface InterpretationEntry {
  role: "user" | "system";
  text: string;
  summary?: string;
  warnings?: string[];
}

export function useSimulation() {
  const [config, setConfig] = useState<PolicyConfig | null>(null);
  const [summary, setSummary] = useState<string>("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [affectedTracts, setAffectedTracts] = useState<string[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<InterpretationEntry[]>([]);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const applyParseResponse = useCallback(
    (res: ParseResponse, userText: string) => {
      setConfig(res.config);
      setSummary(res.summary);
      setWarnings(res.warnings ?? []);
      setAffectedTracts(res.affected_tracts);
      setHistory((prev) => [
        ...prev,
        { role: "user", text: userText },
        {
          role: "system",
          text: res.summary,
          summary: res.summary,
          warnings: res.warnings,
        },
      ]);
    },
    []
  );

  const parsePolicy = useCallback(
    async (text: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await apiParsePolicy(text);
        applyParseResponse(res, text);
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to parse policy";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [applyParseResponse]
  );

  const refinePolicy = useCallback(
    async (text: string) => {
      if (!config) return;
      setIsLoading(true);
      setError(null);
      try {
        const res = await apiRefinePolicy(text, config);
        applyParseResponse(res, text);
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to refine policy";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [config, applyParseResponse]
  );

  const pollStatus = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await getSimulationStatus(id);
        setStatus(s);
        setProgress(s.progress);
        if (s.status === "completed" || s.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // continue polling
      }
    }, 1000);
  }, []);

  const startSimulation = useCallback(async () => {
    if (!config) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiRunSimulation(config);
      setRunId(res.run_id);
      setStatus({
        run_id: res.run_id,
        status: "pending",
        progress: 0,
        current_step: 0,
        total_steps: 260,
      });
      pollStatus(res.run_id);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to start simulation";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [config, pollStatus]);

  const selectScenario = useCallback((scenarioConfig: PolicyConfig) => {
    setConfig(scenarioConfig);
    const desc = (scenarioConfig as Record<string, unknown>).description;
    const name = (scenarioConfig as Record<string, unknown>).name;
    setSummary(String(desc || name || "Predefined scenario selected"));
    setWarnings([]);
    setAffectedTracts(
      ((scenarioConfig as Record<string, unknown>).target_tract_ids as string[] || [])
        .concat((scenarioConfig as Record<string, unknown>).enforcement_target_tracts as string[] || [])
    );
    setHistory([{
      role: "system",
      text: String(desc || name || "Predefined scenario loaded"),
      summary: String(desc || name || ""),
    }]);
    setRunId(null);
    setStatus(null);
    setProgress(0);
    setError(null);
  }, []);

  const reset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    setConfig(null);
    setSummary("");
    setWarnings([]);
    setAffectedTracts([]);
    setRunId(null);
    setStatus(null);
    setProgress(0);
    setError(null);
    setHistory([]);
  }, []);

  return {
    config,
    setConfig,
    summary,
    warnings,
    affectedTracts,
    runId,
    status,
    progress,
    isLoading,
    error,
    history,
    parsePolicy,
    refinePolicy,
    startSimulation,
    selectScenario,
    reset,
  };
}
