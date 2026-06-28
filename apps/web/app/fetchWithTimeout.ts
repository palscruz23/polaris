export class RequestTimeoutError extends Error {
  constructor(message = "Request timed out.") {
    super(message);
    this.name = "RequestTimeoutError";
  }
}

function combineSignals(signals: AbortSignal[]) {
  if (signals.length === 1) {
    return signals[0];
  }

  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any(signals);
  }

  const controller = new AbortController();
  signals.forEach((signal) => {
    if (signal.aborted) {
      controller.abort();
      return;
    }

    signal.addEventListener("abort", () => controller.abort(), {
      once: true,
    });
  });

  return controller.signal;
}

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 12000,
) {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(
    () => timeoutController.abort(),
    timeoutMs,
  );
  const signals = [timeoutController.signal];

  if (init.signal) {
    signals.push(init.signal);
  }

  try {
    return await fetch(input, {
      ...init,
      signal: combineSignals(signals),
    });
  } catch (error) {
    if (timeoutController.signal.aborted && !init.signal?.aborted) {
      throw new RequestTimeoutError();
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
