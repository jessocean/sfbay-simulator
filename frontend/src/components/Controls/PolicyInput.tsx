import React, { useState, useEffect } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  Chip,
  Paper,
  Alert,
  LinearProgress,
  Divider,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import EditIcon from "@mui/icons-material/Edit";
import { getPredefinedScenarios, PredefinedScenario, PolicyConfig } from "../../services/api";
import type { InterpretationEntry } from "../../hooks/useSimulation";
import type { SimulationStatus } from "../../services/api";

interface PolicyInputProps {
  onParse: (text: string) => void;
  onRefine: (text: string) => void;
  onRun: () => void;
  onSelectScenario: (config: PolicyConfig) => void;
  config: PolicyConfig | null;
  summary: string;
  warnings: string[];
  history: InterpretationEntry[];
  isLoading: boolean;
  error: string | null;
  status: SimulationStatus | null;
  progress: number;
}

const PolicyInput: React.FC<PolicyInputProps> = ({
  onParse,
  onRefine,
  onRun,
  onSelectScenario,
  config,
  summary,
  warnings,
  history,
  isLoading,
  error,
  status,
  progress,
}) => {
  const [inputText, setInputText] = useState("");
  const [refineText, setRefineText] = useState("");
  const [showRefine, setShowRefine] = useState(false);
  const [scenarios, setScenarios] = useState<PredefinedScenario[]>([]);

  useEffect(() => {
    getPredefinedScenarios()
      .then(setScenarios)
      .catch(() => {});
  }, []);

  const handleInterpret = () => {
    if (!inputText.trim()) return;
    onParse(inputText.trim());
    setInputText("");
    setShowRefine(false);
  };

  const handleRefine = () => {
    if (!refineText.trim()) return;
    onRefine(refineText.trim());
    setRefineText("");
    setShowRefine(false);
  };

  const handleKeyDown = (
    e: React.KeyboardEvent,
    action: () => void
  ) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      action();
    }
  };

  const isRunning =
    status?.status === "running" || status?.status === "pending";
  const isCompleted = status?.status === "completed";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, p: 2 }}>
      <Typography variant="h6" fontWeight={700} sx={{ mb: 0.5 }}>
        Policy Simulator
      </Typography>

      {/* Predefined scenarios */}
      {!config && scenarios.length > 0 && (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
            Quick start with a predefined scenario:
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {scenarios.map((s) => (
              <Chip
                key={s.id}
                label={s.name}
                size="small"
                variant="outlined"
                clickable
                onClick={() => onSelectScenario(s.config)}
                sx={{ fontSize: "0.75rem" }}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Policy text input */}
      <TextField
        multiline
        minRows={3}
        maxRows={6}
        placeholder="Describe a policy in plain English, e.g. 'Build 50,000 new housing units near BART stations over 5 years'"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        onKeyDown={(e) => handleKeyDown(e, handleInterpret)}
        disabled={isLoading || isRunning}
        fullWidth
        variant="outlined"
        size="small"
      />

      <Button
        variant="contained"
        startIcon={<AutoFixHighIcon />}
        onClick={handleInterpret}
        disabled={!inputText.trim() || isLoading || isRunning}
        fullWidth
      >
        Interpret Policy
      </Button>

      {/* Conversation history */}
      {history.length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1, maxHeight: 240, overflowY: "auto" }}>
          {history.map((entry, i) => (
            <Paper
              key={i}
              variant="outlined"
              sx={{
                p: 1.5,
                bgcolor:
                  entry.role === "user"
                    ? "action.hover"
                    : "background.default",
                borderLeft:
                  entry.role === "system"
                    ? "3px solid"
                    : "none",
                borderLeftColor:
                  entry.role === "system" ? "primary.main" : "transparent",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {entry.role === "user" ? "You" : "Interpretation"}
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.3 }}>
                {entry.text}
              </Typography>
              {entry.warnings && entry.warnings.length > 0 && (
                <Box sx={{ mt: 0.5 }}>
                  {entry.warnings.map((w, j) => (
                    <Alert key={j} severity="warning" sx={{ py: 0, px: 1, mb: 0.3, fontSize: "0.75rem" }}>
                      {w}
                    </Alert>
                  ))}
                </Box>
              )}
            </Paper>
          ))}
        </Box>
      )}

      {/* Parsed config summary */}
      {config && summary && (
        <>
          <Divider />
          <Paper variant="outlined" sx={{ p: 1.5, bgcolor: "background.default" }}>
            <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
              Configuration
            </Typography>
            <Box component="ul" sx={{ pl: 2, m: 0, "& li": { mb: 0.3 } }}>
              {Object.entries(config)
                .slice(0, 8)
                .map(([key, value]) => (
                  <li key={key}>
                    <Typography variant="caption">
                      <strong>{key}:</strong>{" "}
                      {typeof value === "object"
                        ? JSON.stringify(value)
                        : String(value)}
                    </Typography>
                  </li>
                ))}
            </Box>
          </Paper>

          {warnings.length > 0 &&
            warnings.map((w, i) => (
              <Alert key={i} severity="warning" sx={{ py: 0.5 }}>
                {w}
              </Alert>
            ))}

          {/* Refine */}
          {!isRunning && !isCompleted && (
            <>
              {!showRefine ? (
                <Button
                  variant="text"
                  size="small"
                  startIcon={<EditIcon />}
                  onClick={() => setShowRefine(true)}
                >
                  Refine Policy
                </Button>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  <TextField
                    multiline
                    minRows={2}
                    maxRows={4}
                    placeholder="Adjust the policy, e.g. 'Also add rent control at 5% annual cap'"
                    value={refineText}
                    onChange={(e) => setRefineText(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, handleRefine)}
                    disabled={isLoading}
                    fullWidth
                    variant="outlined"
                    size="small"
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleRefine}
                    disabled={!refineText.trim() || isLoading}
                  >
                    Apply Refinement
                  </Button>
                </Box>
              )}
            </>
          )}

          {/* Run button */}
          {!isRunning && !isCompleted && (
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayArrowIcon />}
              onClick={onRun}
              disabled={isLoading}
              fullWidth
              size="large"
            >
              Run Simulation
            </Button>
          )}
        </>
      )}

      {/* Progress */}
      {isRunning && (
        <Box>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            {status?.message ?? "Running simulation..."}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={progress * 100}
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.3, display: "block" }}>
            Step {status?.current_step ?? 0} / {status?.total_steps ?? 260}
          </Typography>
        </Box>
      )}

      {isCompleted && (
        <Alert severity="success" sx={{ py: 0.5 }}>
          Simulation complete. Use the time scrubber to explore results.
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ py: 0.5 }}>
          {error}
        </Alert>
      )}

      {isLoading && !isRunning && <LinearProgress />}
    </Box>
  );
};

export default PolicyInput;
