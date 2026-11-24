import { useEffect, useState } from "react";
import { GeoJsonFeatureCollection } from "@/types/meeting";

export function useRouteRunner(routes: GeoJsonFeatureCollection | null) {
  const [elapsedMinutes, setElapsedMinutes] = useState<number>(0);
  const [maxDuration, setMaxDuration] = useState<number>(15);
  const [isRunning, setIsRunning] = useState<boolean>(false);

  useEffect(() => {
    if (!routes || !routes.features.length) return;
    const peak = Math.max(
      ...routes.features.map((f) => Number(f.properties?.minutes || 5)),
      1
    );
    setMaxDuration(peak);
    setElapsedMinutes(0);
    setIsRunning(true);
  }, [routes]);

  useEffect(() => {
    if (!isRunning) return;
    const step = Math.max(maxDuration / 75, 0.08);
    const interval = setInterval(() => {
      setElapsedMinutes((prev) => {
        if (prev >= maxDuration) {
          setIsRunning(false);
          return maxDuration;
        }
        return Number((prev + step).toFixed(2));
      });
    }, 30);
    return () => clearInterval(interval);
  }, [isRunning, maxDuration]);

  const replayRoute = () => {
    setElapsedMinutes(0);
    setIsRunning(true);
  };

  return { elapsedMinutes, maxDuration, isRunning, replayRoute };
}