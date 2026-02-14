import React, { useState, useCallback } from "react";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  Divider,
} from "@mui/material";
import MapView from "./components/Map/MapView";
import PolicyInput from "./components/Controls/PolicyInput";
import TimeControl from "./components/Controls/TimeControl";
import MetricsPanel from "./components/Dashboard/MetricsPanel";
import { useSimulation } from "./hooks/useSimulation";
import { useMapData } from "./hooks/useMapData";
import { useWebSocket, WSMessage } from "./hooks/useWebSocket";
import { PolicyConfig } from "./services/api";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#42a5f5" },
    secondary: { main: "#ab47bc" },
    background: {
      default: "#121218",
      paper: "#1a1a24",
    },
  },
  typography: {
    fontFamily: "'Inter', 'Roboto', 'Helvetica', sans-serif",
    fontSize: 13,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
  },
});

const App: React.FC = () => {
  const [currentTimestep, setCurrentTimestep] = useState(0);
  const [selectedMetric, setSelectedMetric] = useState("population");

  const sim = useSimulation();
  const { geoJSON } = useMapData(
    sim.status?.status === "completed" ? sim.runId : null,
    currentTimestep
  );

  // WebSocket for live updates
  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.progress !== undefined) {
      // Progress updates are handled via polling in useSimulation,
      // but WebSocket can provide faster updates here if desired.
    }
  }, []);

  useWebSocket(
    sim.status?.status === "running" ? sim.runId : null,
    handleWSMessage
  );

  const handleSelectScenario = useCallback(
    (config: PolicyConfig) => {
      sim.selectScenario(config);
    },
    [sim]
  );

  const highlightAffected =
    sim.affectedTracts.length > 0 && sim.status?.status !== "completed";

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          width: "100vw",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        {/* Main content area */}
        <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Left sidebar */}
          <Box
            sx={{
              width: 400,
              minWidth: 400,
              display: "flex",
              flexDirection: "column",
              bgcolor: "background.paper",
              borderRight: "1px solid",
              borderColor: "divider",
              overflowY: "auto",
            }}
          >
            <PolicyInput
              onParse={sim.parsePolicy}
              onRefine={sim.refinePolicy}
              onRun={sim.startSimulation}
              onSelectScenario={handleSelectScenario}
              config={sim.config}
              summary={sim.summary}
              warnings={sim.warnings}
              history={sim.history}
              isLoading={sim.isLoading}
              error={sim.error}
              status={sim.status}
              progress={sim.progress}
            />
            <Divider />
            <MetricsPanel
              runId={sim.status?.status === "completed" ? sim.runId : null}
              currentTimestep={currentTimestep}
              selectedMetric={selectedMetric}
              onMetricChange={setSelectedMetric}
            />
          </Box>

          {/* Map area */}
          <Box sx={{ flex: 1, position: "relative" }}>
            <MapView
              geoJSON={geoJSON}
              selectedMetric={selectedMetric}
              affectedTracts={sim.affectedTracts}
              highlightAffected={highlightAffected}
            />
          </Box>
        </Box>

        {/* Bottom time control bar */}
        <TimeControl
          currentTimestep={currentTimestep}
          onTimestepChange={setCurrentTimestep}
          disabled={sim.status?.status !== "completed"}
        />
      </Box>
    </ThemeProvider>
  );
};

export default App;
