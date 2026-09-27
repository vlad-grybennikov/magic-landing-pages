import { useCallback, useRef, useState } from "react";

export function useRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const resolveRef = useRef<((blob: Blob) => void) | null>(null);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || "audio/webm",
      });
      stream.getTracks().forEach((track) => track.stop());
      resolveRef.current?.(blob);
      resolveRef.current = null;
    };

    recorderRef.current = recorder;
    recorder.start();
    setIsRecording(true);
  }, []);

  const stop = useCallback(() => {
    return new Promise<Blob>((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(new Blob());
        return;
      }
      resolveRef.current = resolve;
      recorder.stop();
      setIsRecording(false);
    });
  }, []);

  return { isRecording, start, stop };
}
