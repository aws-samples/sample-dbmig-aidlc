CREATE UNIQUE NONCLUSTERED INDEX [AK_Shift_StartTime_EndTime]
    ON [HumanResources].[Shift] ([StartTime] ASC, [EndTime] ASC);