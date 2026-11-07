namespace Fulfillment.Application;

// Reference-harness-only synchronization. The parent kills this process after
// observing the marker; no HTTP control surface or timing-dependent crash guess.
public static class CrashBarrier
{
    public static async Task Reach(string point)
    {
        if (Environment.GetEnvironmentVariable("EVAL_CRASH_POINT") != point) return;
        var marker = Environment.GetEnvironmentVariable("EVAL_CRASH_MARKER")
            ?? throw new InvalidOperationException("Missing test marker path.");
        await File.WriteAllTextAsync(marker, point);
        await Task.Delay(Timeout.InfiniteTimeSpan);
    }
}
