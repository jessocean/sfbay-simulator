import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  Box,
  Slider,
  IconButton,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import SkipPreviousIcon from "@mui/icons-material/SkipPrevious";

const START_DATE = new Date(2025, 0, 1); // Jan 1, 2025
const MAX_STEP = 26;

function stepToDate(step: number): string {
  const d = new Date(START_DATE);
  d.setDate(d.getDate() + step * 14);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: undefined,
  });
}

function stepToFullDate(step: number): string {
  const d = new Date(START_DATE);
  d.setDate(d.getDate() + step * 14);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface TimeControlProps {
  currentTimestep: number;
  onTimestepChange: (step: number) => void;
  disabled: boolean;
}

const TimeControl: React.FC<TimeControlProps> = ({
  currentTimestep,
  onTimestepChange,
  disabled,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepRef = useRef(currentTimestep);

  stepRef.current = currentTimestep;

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const play = useCallback(() => {
    stop();
    setIsPlaying(true);
    const ms = Math.max(50, 500 / speed);
    intervalRef.current = setInterval(() => {
      const next = stepRef.current + 1;
      if (next > MAX_STEP) {
        stop();
        return;
      }
      onTimestepChange(next);
    }, ms);
  }, [speed, onTimestepChange, stop]);

  // Restart interval when speed changes while playing
  useEffect(() => {
    if (isPlaying) {
      play();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  const handleTogglePlay = () => {
    if (isPlaying) {
      stop();
    } else {
      play();
    }
  };

  const handleReset = () => {
    stop();
    onTimestepChange(0);
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        px: 3,
        py: 1,
        bgcolor: "background.paper",
        borderTop: "1px solid",
        borderColor: "divider",
        minHeight: 56,
      }}
    >
      <IconButton
        size="small"
        onClick={handleReset}
        disabled={disabled}
        title="Reset to start"
      >
        <SkipPreviousIcon />
      </IconButton>

      <IconButton
        size="small"
        onClick={handleTogglePlay}
        disabled={disabled}
        color={isPlaying ? "warning" : "primary"}
        title={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
      </IconButton>

      <Typography
        variant="body2"
        sx={{ minWidth: 90, textAlign: "center", fontWeight: 600 }}
      >
        {stepToFullDate(currentTimestep)}
      </Typography>

      <Slider
        value={currentTimestep}
        min={0}
        max={MAX_STEP}
        step={1}
        onChange={(_, val) => {
          if (typeof val === "number") {
            onTimestepChange(val);
          }
        }}
        disabled={disabled}
        valueLabelDisplay="auto"
        valueLabelFormat={stepToDate}
        sx={{ flex: 1, mx: 1 }}
      />

      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 70 }}>
        Step {currentTimestep}/{MAX_STEP}
      </Typography>

      <ToggleButtonGroup
        value={speed}
        exclusive
        onChange={(_, val) => {
          if (val !== null) setSpeed(val);
        }}
        size="small"
      >
        <ToggleButton value={1} sx={{ px: 1, py: 0.3, fontSize: "0.7rem" }}>
          1x
        </ToggleButton>
        <ToggleButton value={2} sx={{ px: 1, py: 0.3, fontSize: "0.7rem" }}>
          2x
        </ToggleButton>
        <ToggleButton value={5} sx={{ px: 1, py: 0.3, fontSize: "0.7rem" }}>
          5x
        </ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
};

export default TimeControl;
