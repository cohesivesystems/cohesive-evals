"""Visible quantity-limit examples. Run with the original contract_tests client."""
SEED = {'orders':[{'id':x,'status':'Draft'} for x in ['limit-visible-ok','limit-visible-over']],
        'inventory':[{'sku':'limit-visible','available':5}], 'reservations':[]}


def exercise(Client, url):
    c=Client(url)
    c.expect('limit default','GET','/inventory/limit-visible',200,
             expected={'sku':'limit-visible','available':5,'maxPerOrder':2147483647})
    c.expect('configure limit','PUT','/inventory/limit-visible/quantity-limit',200,{'maxPerOrder':2},
             expected={'sku':'limit-visible','available':5,'maxPerOrder':2})
    c.fulfill('visible-over','limit-visible-over','limit-visible',3,'QuantityLimitExceeded')
    c.fulfill('visible-at','limit-visible-ok','limit-visible',2,'ReservedAndSubmitted')
    c.expect('rejection preserves stock','GET','/inventory/limit-visible',200,
             expected={'sku':'limit-visible','available':3,'maxPerOrder':2})
    return c.observations
