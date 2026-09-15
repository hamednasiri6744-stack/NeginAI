-- Synthetic downstream confirmation seam: intentionally NOT full ERP validation.
CREATE SCHEMA FRU;
GO
CREATE TABLE gnr.tblGeneralConfig(KeyName varchar(100),KeyValue varchar(100));
CREATE TABLE gnr.tblServerConfig(KeyName varchar(100),KeyValue varchar(100));
CREATE TABLE dbo.CreditTestSwitch(ConfirmError bit,WrongSourceDelta bit,DestinationChanged bit,CreateDebit bit,MissingConfirmation bit);
INSERT dbo.CreditTestSwitch VALUES(0,0,0,0,0);
GO
CREATE PROCEDURE FRU.usp_VocherConfirmation @AccYear int,@DCRef int,@UserRef int,@VocherHdrRef int,@IsConfirm bit,
 @ErrMsg nvarchar(max) OUTPUT,@ResultMsg varchar(max) OUTPUT
AS
BEGIN
 SET NOCOUNT ON;
 UPDATE H SET ConfirmedBy=@UserRef,ConfirmDate=GETDATE() FROM inv.tblVocherHdr H WHERE ID=@VocherHdrRef
  AND NOT EXISTS(SELECT 1 FROM dbo.CreditTestSwitch WHERE MissingConfirmation=1);
 UPDATE SG SET OnHandQty=OnHandQty-I.TotalQty
  FROM gnr.tblStockGoods SG JOIN inv.tblVocherItm I ON I.GoodsRef=SG.GoodsRef
  JOIN inv.tblVocherHdr H ON H.ID=I.HdrRef AND H.StockDCRef=SG.StockDCRef AND H.AccYear=SG.AccYear
  WHERE H.ID=@VocherHdrRef;
 IF EXISTS(SELECT 1 FROM dbo.CreditTestSwitch WHERE WrongSourceDelta=1)
  UPDATE gnr.tblStockGoods SET OnHandQty=OnHandQty-1 WHERE StockDCRef=(SELECT StockDCRef FROM inv.tblVocherHdr WHERE ID=@VocherHdrRef);
 IF EXISTS(SELECT 1 FROM dbo.CreditTestSwitch WHERE DestinationChanged=1)
  UPDATE gnr.tblStockGoods SET OnHandQty=OnHandQty+1 WHERE StockDCRef=(SELECT TStockDCRef FROM inv.tblVocherHdr WHERE ID=@VocherHdrRef);
 IF EXISTS(SELECT 1 FROM dbo.CreditTestSwitch WHERE CreateDebit=1)
  INSERT inv.tblVocherHdr(ID,StockDCRef,VocherNo,VocherTypeCode,HealthCodeType,HealthCode,VocherDate,AccYear,UserRef,ModifiedDate)
   SELECT ID+10000,TStockDCRef,VocherNo,15,1047,1,VocherDate,AccYear,UserRef,GETDATE() FROM inv.tblVocherHdr WHERE ID=@VocherHdrRef;
 -- Native FRU success actually returns CRLF; regression must exercise this.
 SET @ErrMsg=CASE WHEN EXISTS(SELECT 1 FROM dbo.CreditTestSwitch WHERE ConfirmError=1) THEN N'synthetic native failure' ELSE CHAR(10)+CHAR(13)+CHAR(9) END;
 SET @ResultMsg='confirmed';
END;
GO
