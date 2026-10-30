CREATE TABLE [HumanResources].[JobCandidate](
[JobCandidateID] int IDENTITY(1, 1) NOT NULL,
[BusinessEntityID] int NULL,
[Resume] xml NULL,
[ModifiedDate] datetime NOT NULL DEFAULT (getdate())
)
ON [PRIMARY];