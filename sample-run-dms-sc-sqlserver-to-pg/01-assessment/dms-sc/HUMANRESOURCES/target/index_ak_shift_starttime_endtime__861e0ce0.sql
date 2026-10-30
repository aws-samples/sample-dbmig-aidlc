CREATE UNIQUE INDEX ix_shift_ak_shift_starttime_endtime
ON adventureworks_humanresources.shift
USING BTREE (starttime ASC, endtime ASC);