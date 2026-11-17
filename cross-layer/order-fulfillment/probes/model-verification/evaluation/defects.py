"""Evaluator-owned production faults. Never copied into candidate fixture directories."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Defect:
    name: str
    assertion: str
    path: str
    before: str
    after: str
    start: str = ""
    end: str = ""


def defects(condition):
    if condition == 'conventional':
        path = 'src/Fulfillment.Application/Domain.cs'
        rows = [
            ('zero-admitted', 'domain outcome', 'quantity <= 0 ?', 'quantity < 0 ?'),
            ('quarantine-omitted', 'domain outcome', ': item.Quarantined ? (item, StockOutcome.InventoryQuarantined)\n        ', ''),
            ('limit-omitted', 'domain outcome', ': quantity > item.MaxPerOrder ? (item, StockOutcome.QuantityLimitExceeded)\n        ', ''),
            ('stock-omitted', 'domain outcome', ': item.Available < quantity ? (item, StockOutcome.InsufficientStock)\n        ', ''),
            ('stock-too-strict', 'domain outcome', 'item.Available < quantity ?', 'item.Available <= quantity ?'),
            ('limit-too-strict', 'domain outcome', 'quantity > item.MaxPerOrder ?', 'quantity >= item.MaxPerOrder ?'),
            ('decrement-omitted', 'accepted delta', 'Available = item.Available - quantity', 'Available = item.Available'),
            ('reject-all', 'domain outcome', 'quantity <= 0 ?', 'true ?'),
            ('configuration-corrupted', 'accepted delta', 'Available = item.Available - quantity', 'Available = item.Available - quantity, MaxPerOrder = 0'),
        ]
        result = [Defect(n, a, path, b, c) for n, a, b, c in rows]
        result.append(Defect('wrong-terminal', 'terminal outcome', 'src/Fulfillment.Application/FulfillmentResults.cs',
                             'StockOutcome.InvalidQuantity => "InvalidQuantity"', 'StockOutcome.InvalidQuantity => "InsufficientStock"'))
        return result
    if condition != 'cohesive':
        raise ValueError(condition)
    path = 'src/Fulfillment.Application/FulfillmentDomain.cs'
    def guard(predicate, outcome):
        return f'                .Requires((item, input) => {predicate},\n                    (_, _) => new StockResult(StockOutcome.{outcome}, FulfillmentOutcome.{outcome}))\n'
    positive = guard('input.Quantity > 0', 'InvalidQuantity')
    rows = [
        ('zero-admitted', 'domain outcome', positive, positive.replace('> 0', '>= 0')),
        ('quarantine-omitted', 'domain outcome', guard('!item.Quarantined', 'InventoryQuarantined'), ''),
        ('limit-omitted', 'domain outcome', guard('input.Quantity <= item.MaxPerOrder', 'QuantityLimitExceeded'), ''),
        ('stock-omitted', 'domain outcome', guard('item.Available >= input.Quantity', 'InsufficientStock'), ''),
        ('stock-too-strict', 'domain outcome', 'item.Available >= input.Quantity,', 'item.Available > input.Quantity,'),
        ('limit-too-strict', 'domain outcome', 'input.Quantity <= item.MaxPerOrder,', 'input.Quantity < item.MaxPerOrder,'),
        ('decrement-omitted', 'accepted delta', 'item.Available - input.Quantity)', 'item.Available)'),
        ('reject-all', 'domain outcome', positive, positive.replace('input.Quantity > 0', 'input.Quantity > int.MaxValue')),
        ('configuration-corrupted', 'accepted delta',
         '.Set(new("stock/update"), item => item.Available, (item, input) => item.Available - input.Quantity)',
         '.Set(new("stock/update"), item => item.Available, (item, input) => item.Available - input.Quantity)\n                .Set(new("fault/configuration"), item => item.MaxPerOrder, (_, _) => 0)'),
        ('wrong-terminal', 'terminal outcome', positive, positive.replace('FulfillmentOutcome.InvalidQuantity', 'FulfillmentOutcome.InsufficientStock')),
    ]
    return [Defect(n, a, path, b, c, "        Reserve = inventory.Transition", "        Release = inventory.Transition") for n, a, b, c in rows]


def apply(root, defect):
    path = root / defect.path
    source = path.read_text()
    region = source
    if defect.start:
        if source.count(defect.start) != 1 or source.count(defect.end) != 1:
            raise ValueError('Ambiguous mutation region')
        region = source[source.index(defect.start):source.index(defect.end)]
    count = region.count(defect.before)
    if count != 1:
        raise ValueError(f'{defect.name}: expected one anchor, found {count}')
    path.write_text(source.replace(region, region.replace(defect.before, defect.after)))
