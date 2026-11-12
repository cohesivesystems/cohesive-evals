namespace Fulfillment.Application;

// Reference-harness-only synchronization. The parent kills this process after
// observing the marker; no HTTP control surface or timing-dependent crash guess.
public static class CrashBarrier
{
    public static async Task Reach(string point)
    {
        if (Environment.GetEnvironmentVariable("EVAL_FAIL_POINT") == point)
        {
            var failureMarker = Environment.GetEnvironmentVariable("EVAL_FAIL_MARKER")
                ?? throw new InvalidOperationException("Missing failure marker path.");
            bool first;
            try { using var file = new FileStream(failureMarker, FileMode.CreateNew); first = true; }
            catch (IOException) when (File.Exists(failureMarker)) { first = false; }
            if (first) throw new InvalidOperationException("Injected terminal activity failure: " + point);
        }
        if (Environment.GetEnvironmentVariable("EVAL_CRASH_POINT") != point) return;
        var marker = Environment.GetEnvironmentVariable("EVAL_CRASH_MARKER")
            ?? throw new InvalidOperationException("Missing test marker path.");
        await File.WriteAllTextAsync(marker, point);
        await Task.Delay(Timeout.InfiniteTimeSpan);
    }
}
