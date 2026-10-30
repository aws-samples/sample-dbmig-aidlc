CREATE TABLE [dbo].[DatabaseLog](
[DatabaseLogID] int IDENTITY(1, 1) NOT NULL,
[PostTime] datetime NOT NULL,
[DatabaseUser] nvarchar(128) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[Event] nvarchar(128) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[Schema] nvarchar(128) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[Object] nvarchar(128) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
[TSQL] nvarchar(max) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
[XmlEvent] xml NOT NULL
)
ON [PRIMARY] TEXTIMAGE_ON [PRIMARY];