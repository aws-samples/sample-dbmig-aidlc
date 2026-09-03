CREATE UNIQUE INDEX ix_shift_ak_shift_starttime_endtime
ON humanresources.shift
USING BTREE (starttime ASC, endtime ASC);