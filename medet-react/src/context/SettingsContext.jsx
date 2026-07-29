import { createContext, useContext, useMemo, useState } from "react";

const DEFAULTS = {
  yoloLow: 0.25,
  yoloHigh: 0.9,
  frameSkip: 5,
  minSegmentDuration: 0.5,
};

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [yoloLow, setYoloLow] = useState(DEFAULTS.yoloLow);
  const [yoloHigh, setYoloHigh] = useState(DEFAULTS.yoloHigh);
  const [frameSkip, setFrameSkip] = useState(DEFAULTS.frameSkip);
  const [minSegmentDuration, setMinSegmentDuration] = useState(DEFAULTS.minSegmentDuration);

  const value = useMemo(
    () => ({
      yoloLow,
      yoloHigh,
      frameSkip,
      minSegmentDuration,
      setYoloLow,
      setYoloHigh,
      setFrameSkip,
      setMinSegmentDuration,
      // Seuil d'écart (secondes) utilisé pour fusionner les segments en
      // mode live, repris de app2.py : (frame_skip / 25 fps) * 3
      gapThresholdSeconds: (frameSkip / 25) * 3,
    }),
    [yoloLow, yoloHigh, frameSkip, minSegmentDuration]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings doit être utilisé dans <SettingsProvider>");
  return ctx;
}
