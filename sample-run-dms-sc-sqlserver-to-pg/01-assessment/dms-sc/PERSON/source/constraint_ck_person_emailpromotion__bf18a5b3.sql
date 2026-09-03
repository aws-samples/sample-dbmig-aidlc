ALTER TABLE [Person].[Person]
ADD CONSTRAINT [CK_Person_EmailPromotion] CHECK (([EmailPromotion]>=(0) AND [EmailPromotion]<=(2)));