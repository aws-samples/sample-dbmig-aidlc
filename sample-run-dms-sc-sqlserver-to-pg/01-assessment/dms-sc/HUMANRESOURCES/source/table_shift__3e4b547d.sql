CREATE TABLE [HumanResources].[Shift](
[ShiftID] tinyint IDENTITY(1, 1) NOT NULL,
[Name] Name NOT NULL,
[StartTime] time(7) NOT NULL,
[EndTime] time(7) NOT NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];