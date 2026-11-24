# Discover single-step Ship cases

Submit Cases.cs implementing Cases.Propose(). Return an array of (OrderStatus Status, bool Hold) tuples, at most ten unique pairs. You have eight minutes wall-clock including build and rehearsal; you may finish early. Use the production domain and any supplied condition libraries. Use deterministic generation. The grader freezes your output on the clean reference before running any defects.

An order may Ship only from Packed when its shipping hold is clear. Success moves it to Shipped. Rejection preserves the status. Every decision preserves the order ID and the hold. Repeat Ship is rejected. The benchmark supplies an independent oracle and execution adapter; your task is case selection. You can build with dotnet build Suite/Suite.csproj and rehearse with dotnet run --project Suite --no-build -- propose.
