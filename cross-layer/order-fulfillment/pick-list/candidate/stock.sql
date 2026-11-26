CREATE TABLE IF NOT EXISTS pick_stock (
    location text NOT NULL,
    sku text NOT NULL,
    units integer NOT NULL CHECK (units >= 0),
    PRIMARY KEY (location, sku)
);
