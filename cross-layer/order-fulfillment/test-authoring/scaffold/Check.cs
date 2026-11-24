using System.Text.Json;

internal static class Check
{
    public static void Equal<T>(string label, T expected, T actual)
    {
        bool passed = EqualityComparer<T>.Default.Equals(expected, actual);
        Console.WriteLine(JsonSerializer.Serialize(new { label, expected, actual, passed }));
        if (!passed) Environment.Exit(10);
    }
}
