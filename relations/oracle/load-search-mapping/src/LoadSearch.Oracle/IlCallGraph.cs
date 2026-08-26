using System.Reflection;
using System.Reflection.Emit;

namespace LoadSearch.Oracle;

sealed record MethodCall(MethodBase Caller, MethodBase Callee);

static class IlCallGraph
{
    static readonly OpCode[] OneByte = new OpCode[0x100];
    static readonly OpCode[] TwoByte = new OpCode[0x100];

    static IlCallGraph()
    {
        foreach (var field in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static))
        {
            if (field.GetValue(null) is not OpCode opcode)
                continue;

            var value = unchecked((ushort)opcode.Value);
            if (value < 0x100)
                OneByte[value] = opcode;
            else if ((value & 0xff00) == 0xfe00)
                TwoByte[value & 0xff] = opcode;
        }
    }

    public static IReadOnlyList<MethodCall> ReachableCalls(MethodBase entryPoint)
    {
        var assembly = entryPoint.DeclaringType?.Assembly
            ?? throw new InvalidOperationException("Entry point has no declaring assembly.");
        Queue<MethodBase> pending = new([entryPoint]);
        HashSet<(Module Module, int Token)> visited = [];
        List<MethodCall> calls = [];

        while (pending.TryDequeue(out var caller))
        {
            if (!visited.Add((caller.Module, caller.MetadataToken)))
                continue;

            foreach (var callee in DirectCalls(caller))
            {
                calls.Add(new(caller, callee));
                if (callee.DeclaringType?.Assembly == assembly && callee.GetMethodBody() is not null)
                    pending.Enqueue(callee);
            }
        }

        return calls;
    }

    static IEnumerable<MethodBase> DirectCalls(MethodBase method)
    {
        var il = method.GetMethodBody()?.GetILAsByteArray();
        if (il is null)
            yield break;

        var position = 0;
        while (position < il.Length)
        {
            var opcode = ReadOpcode(il, ref position);
            if (opcode.OperandType == OperandType.InlineMethod)
            {
                var token = ReadInt32(il, ref position);
                MethodBase? called = null;
                try
                {
                    called = method.Module.ResolveMethod(
                        token,
                        method.DeclaringType?.GetGenericArguments(),
                        method.IsGenericMethod ? method.GetGenericArguments() : null);
                }
                catch (ArgumentException)
                {
                    // An unresolvable token is not silently treated as treatment evidence.
                }

                if (called is not null)
                    yield return called;
                continue;
            }

            SkipOperand(opcode.OperandType, il, ref position);
        }
    }

    static OpCode ReadOpcode(byte[] il, ref int position)
    {
        var first = il[position++];
        return first == 0xfe ? TwoByte[il[position++]] : OneByte[first];
    }

    static int ReadInt32(byte[] il, ref int position)
    {
        var value = BitConverter.ToInt32(il, position);
        position += sizeof(int);
        return value;
    }

    static void SkipOperand(OperandType operandType, byte[] il, ref int position)
    {
        position += operandType switch
        {
            OperandType.InlineNone => 0,
            OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar => 1,
            OperandType.InlineVar => 2,
            OperandType.InlineBrTarget or OperandType.InlineField or OperandType.InlineI
                or OperandType.InlineSig or OperandType.InlineString or OperandType.InlineTok
                or OperandType.InlineType or OperandType.ShortInlineR => 4,
            OperandType.InlineI8 or OperandType.InlineR => 8,
            OperandType.InlineSwitch => sizeof(int) + (ReadSwitchCount(il, position) * sizeof(int)),
            _ => throw new InvalidOperationException($"Unsupported IL operand type '{operandType}'.")
        };
    }

    static int ReadSwitchCount(byte[] il, int position) => BitConverter.ToInt32(il, position);
}
