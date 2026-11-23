"""Matched lifecycle defects with exact source anchors and independent named grading assertions."""
EXPECTED_ASSERTIONS = {
    'pack-draft': 'Draft pack', 'unpack-to-draft': 'Packed unpack',
    'lose-packed': 'packed survives restart', 'stock-on-repeat': 'stock and reservation preservation',
}


def mutations(condition):
    """Return source mutations for one implementation; shutdown and repeat controls use its physical tables."""
    conventional = condition == 'conventional'
    table = 'orders' if conventional else 'cohesive_orders'
    inventory = 'inventory' if conventional else 'cohesive_inventory'
    domain = 'Domain.cs' if conventional else 'FulfillmentDomain.cs'
    draft = '.Permit(OrderCommand.Submit, OrderStatus.Submitted)' if conventional else 'machine.Edge("pack").From(submitted)'
    wrong_draft = draft + '\n            .Permit(OrderCommand.Pack, OrderStatus.Packed)' if conventional else draft.replace('From(submitted)', 'From(draft)')
    unpack = '.Permit(OrderCommand.Unpack, OrderStatus.Submitted)' if conventional else 'machine.Edge("unpack").From(packed).To(submitted)'
    wrong_unpack = unpack.replace('OrderStatus.Submitted', 'OrderStatus.Draft') if conventional else unpack.replace('To(submitted)', 'To(draft)')
    anchor = 'HostSetup.Configure(app);'
    lose_packed = f'''
app.Lifetime.ApplicationStopping.Register(() =>
{{
    using var cmd = app.Services.GetRequiredService<NpgsqlDataSource>().CreateCommand(
        "UPDATE {table} SET status='Submitted' WHERE status='Packed'");
    cmd.ExecuteNonQuery();
}});
'''
    stock_on_repeat = f'''
app.Use(async (context, next) =>
{{
    var path = context.Request.Path.Value?.Split('/');
    if (context.Request.Method == "POST" && path is ["", "orders", var id, "pack"] &&
        await app.Services.GetRequiredService<IFulfillmentBackend>().GetOrder(id) is {{ Status: "Packed" }})
    {{
        await using var cmd = app.Services.GetRequiredService<NpgsqlDataSource>().CreateCommand(
            "UPDATE {inventory} SET available=available-1 WHERE available>0");
        await cmd.ExecuteNonQueryAsync();
    }}
    await next();
}});
'''
    return {
        'pack-draft': (domain, draft, wrong_draft, 'lifecycle'),
        'unpack-to-draft': (domain, unpack, wrong_unpack, 'lifecycle'),
        'lose-packed': ('Program.cs', anchor, anchor + lose_packed, 'lifecycle'),
        'stock-on-repeat': ('Program.cs', anchor, anchor + stock_on_repeat, 'lifecycle'),
    }
