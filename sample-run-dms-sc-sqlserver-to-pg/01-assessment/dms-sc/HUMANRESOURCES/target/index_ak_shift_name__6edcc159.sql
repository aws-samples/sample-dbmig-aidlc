CREATE UNIQUE INDEX ix_shift_ak_shift_name
ON adventureworks_humanresources.shift
USING BTREE (name ASC);