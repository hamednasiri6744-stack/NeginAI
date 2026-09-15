-- Synthetic schema only. Official allocation/creation procedure bodies are copied verbatim below.
CREATE SCHEMA gnr;
GO
CREATE SCHEMA inv;
GO
CREATE SCHEMA idgen;
GO
CREATE SCHEMA SLE;
GO
CREATE TABLE inv.tblVocherHdr (
[ID] int NOT NULL PRIMARY KEY,
[StockDCRef] int NOT NULL,
[VocherNo] int NOT NULL,
[VocherTypeCode] int NOT NULL,
[HealthCodeType] int NOT NULL,
[HealthCode] int NOT NULL,
[VocherDate] varchar(10) NOT NULL,
[TVocherNo] int NULL,
[TVocherTypeCode] int NULL,
[TStockDCRef] int NULL,
[AccYear] int NOT NULL,
[UserRef] int NOT NULL,
[DCRef] int NULL,
[DocRef] int NULL,
[Comment] varchar(255) NULL,
[SupplierRef] int NULL,
[ModifiedDate] datetime NOT NULL,
[ConfirmedBy] int NULL,
[ReferenceNo] varchar(20) NULL,
[ConfirmDate] datetime NULL,
[ICAStatus] int NULL,
[IsMerge] bit NOT NULL DEFAULT 0,
[CustRef] int NULL,
[TICAHdrRef] int NULL,
[ICAStockDCRef] int NULL,
[TVchTypeRef] int NULL,
[TadilICAHdrRef] int NULL,
[UniqueId] uniqueidentifier NULL,
[PurchaseOrderRef] int NULL,
[SaleExitRef] int NULL,
[GoodsBundleRef] int NULL,
[TrackingNo] int NULL,
[LoadStationRef] int NULL,
[ProductionRef] int NULL,
[DeliveryRef] int NULL,
[SystemId] int NULL,
[DLId] int NULL,
[FifthLedgerId] int NULL,
[SixthLedgerId] int NULL,
[SeventhLedgerId] int NULL,
[ChangeTimeStamp] timestamp,
[CreationDate] datetime NULL,
[HostName] varchar(100) NULL,
[WinUserName] varchar(100) NULL,
[SQLUserName] varchar(100) NULL,
[ApplicationName] varchar(100) NULL,
[TadillType] int NULL,
[ForSetBatch] bit NULL
);
GO
CREATE TABLE inv.tblVocherItm (
[ID] int NOT NULL PRIMARY KEY,
[HdrRef] int NOT NULL,
[RowOrder] real NOT NULL,
[GoodsRef] int NOT NULL,
[UnitRef] int NOT NULL,
[UnitCapacity] decimal(18,6) NULL,
[UnitQty] decimal(18,6) NULL,
[TotalQty] decimal(18,6) NULL,
[AccYear] int NOT NULL,
[TICAItmRef] int NULL,
[ValuePrice] money NULL,
[Comment] varchar(255) NULL,
[ModifiedBy] int NULL
);
GO
CREATE UNIQUE INDEX UX_Number ON inv.tblVocherHdr(AccYear,StockDCRef,VocherTypeCode,VocherNo);
CREATE TABLE inv.tblVocherItmDetail(ID int PRIMARY KEY,ItmRef int,BatchNoRef int,TotalQty decimal(18,6),Comment varchar(255),Price money);
CREATE SEQUENCE idgen.tblVocherItm_Sequence AS int START WITH 1;
CREATE SEQUENCE idgen.tblVocherItmDetail_Sequence AS int START WITH 1;
CREATE SEQUENCE idgen.TestHeaderId AS int START WITH 1;
CREATE TABLE dbo.tblVocherNo(VocherType int,StockDcRef int,AccYear int,VocherNo int,PRIMARY KEY(VocherType,StockDcRef,AccYear));
CREATE TABLE dbo.AppUser(AppUserId int PRIMARY KEY,IsActive bit,IsDeleted bit);
CREATE TABLE gnr.tblAccYear(AccYear int,StartDate varchar(10),EndDate varchar(10));
CREATE TABLE gnr.tblStockDC(ID int PRIMARY KEY,DCRef int,InActiveAccYear int);
CREATE TABLE gnr.tblOprDate(AccYear int,DCRef int,SysRef int,IsClosed bit,LastDate varchar(10),OprDate varchar(10));
CREATE TABLE inv.tblStCountHdr(StockDCRef int,AccYear int,DocStatus int);
CREATE TABLE gnr.tblGoods(ID int PRIMARY KEY,GoodsCode varchar(80),UnitRef int,GoodsTypeRef int,SerialNo decimal(18,0),UseBatchPackage int);
CREATE TABLE gnr.tblSupplier(Id int PRIMARY KEY,SupplierName nvarchar(255),Active bit);
CREATE TABLE gnr.tblGoodsSupplier(GoodsRef int,SupplierRef int);
CREATE TABLE gnr.tblStockGoods(GoodsRef int,StockDCRef int,AccYear int,IsBatch bit,OnHandQty decimal(18,6),
 DamagedQty decimal(18,6) DEFAULT 0,UnDeliveredQty decimal(18,6) DEFAULT 0,ReservedQty decimal(18,6) DEFAULT 0);
CREATE TABLE gnr.tblPackage(GoodsRef int,UnitRef int,Qty decimal(18,6),ForInv bit,Status bit);
CREATE TABLE SLE.tblGoodsNoSale(GoodsRef int,DCRef int,Status int,StartDate varchar(10),EndDate varchar(10));
CREATE TABLE dbo.TestSwitch(ValidationError bit NOT NULL,ForceConfirmed bit NOT NULL,CorruptItem bit NOT NULL,ChangeStock bit NOT NULL);
INSERT dbo.TestSwitch VALUES(0,0,0,0);
GO
CREATE PROCEDURE gnr.uspGetNextId @TableName varchar(200),@NextId int OUTPUT AS
BEGIN SELECT @NextId=NEXT VALUE FOR idgen.TestHeaderId; END;
GO
CREATE FUNCTION dbo.ufn_DateIsValid(@AccYear int,@Date varchar(10)) RETURNS int AS
BEGIN RETURN CASE WHEN EXISTS(SELECT 1 FROM gnr.tblAccYear WHERE AccYear=@AccYear AND @Date BETWEEN StartDate AND EndDate) THEN 1 ELSE 0 END; END;
GO
-- Test double: isolates failure of the downstream validator; not a copy of all ERP business validation.
CREATE PROCEDURE inv.usp_VocherValidation @HdrRef int,@VocherTypeCode int,@DocRef int,@ErrMsg varchar(max) OUTPUT AS
BEGIN SET @ErrMsg=CASE WHEN EXISTS(SELECT 1 FROM dbo.TestSwitch WHERE ValidationError=1) THEN 'synthetic validation error' ELSE '' END; END;
GO
CREATE TRIGGER inv.TestConfirmation ON inv.tblVocherHdr AFTER INSERT AS
BEGIN IF EXISTS(SELECT 1 FROM dbo.TestSwitch WHERE ForceConfirmed=1)
 UPDATE H SET ConfirmedBy=10,ConfirmDate=GETDATE() FROM inv.tblVocherHdr H JOIN inserted I ON H.ID=I.ID; END;
GO
CREATE TRIGGER inv.TestItemCorruption ON inv.tblVocherItm AFTER INSERT AS
BEGIN IF EXISTS(SELECT 1 FROM dbo.TestSwitch WHERE CorruptItem=1)
 UPDATE L SET TotalQty=L.TotalQty+1 FROM inv.tblVocherItm L JOIN inserted I ON L.ID=I.ID;
 IF EXISTS(SELECT 1 FROM dbo.TestSwitch WHERE ChangeStock=1) UPDATE gnr.tblStockGoods SET OnHandQty=OnHandQty+1;
 END;
GO
CREATE PROCEDURE dbo.GetMaxVocherNo    
 @VocherType int    
 , @StockDcRef int    
 , @AccYear int    
 , @VocherNo int output    
 , @WithSelect int = 1 
 , @Count INT = 1    
as begin    
	set nocount on    
	declare @tranID varchar(40)    
	set @tranID = newid()   
	CREATE TABLE #tmpVocher (VocherNo INT)     
	begin tran @tranID    
		update dbo.tblVocherNo set VocherNo = VocherNo + @Count   
		OUTPUT inserted.VocherNo      
		INTO #tmpVocher     
		where StockDcRef = @StockDcRef and AccYear = @AccYear and VocherType=@VocherType    
		if (@@rowcount = 0) begin    
			insert into dbo.tblVocherNo (VocherNo,VocherType, StockDcRef, AccYear)    
			OUTPUT inserted.VocherNo      
			INTO #tmpVocher     
			select isnull(max(VocherNo), 0) + 1,@VocherType, @StockDcRef, @AccYear    
			from inv.tblvocherHdr with(nolock)    
			where VocherTypeCode=@VocherType and StockDcRef = @StockDcRef and AccYear = @AccYear and VocherNo > 0    
		end    
		select @VocherNo = VocherNo from #tmpVocher  
		SELECT @VocherNo = @VocherNo - @Count + 1 
 --declare @MaxVocherNo int    
 --select @MaxVocherNo = max(VocherNo)    
 --from inv.tblvocherHdr sh with(nolock)    
 --where VocherTypeCode=@VocherType and AccYear=@AccYear and StockDcRef=@StockDcRef and VocherNo>=@VocherNo    
 --if @MaxVocherNo is not null and @MaxVocherNo>=@VocherNo    
 --begin    
 -- set @VocherNo=@MaxVocherNo+1    
  --update dbo.tblVocherNo set VocherNo = @VocherNo where StockDcRef = @StockDcRef and AccYear = @AccYear and VocherType=@VocherType    
 --end    
	if @WithSelect=1 select @VocherNo    
	commit tran @tranID    
end 
GO
-- Number: 2545 From: 4998
-- DocumentRef: 196805
-- Project: SDS.NET-SDS
-- ProductVersion: SDS 5.9.0
-- Version: 5.9.0
-- Done by : رعنا
------------------------------
--usp_DBApi_CreateInvVocher-6
CREATE proc usp_DBApi_CreateInvVocher @AppUserId int, @AccYear int, @DCRef int, @VocherId int output, @VocherNo int output, @DontChangeUnitQty bit=0
as
begin
	/*
		create table #apiVocher (
			VocherNo int, StockDCRef int, VocherTypeCode int, HealthCodeType int, HealthCode int, VocherDate char(10), TVocherNo int, TVocherTypeCode int, TStockDCRef int,
			SupplierRef int, ModifiedDate datetime, ConfirmedBy int, ConfirmDate datetime, ReferenceNo int, ICAStatus int, IsMerge int, CustRef int, 
			TICAHdrRef int, ICAStockDCRef int, TVchTypeRef int, TadilICAHdrRef int, UniqueId uniqueidentifier, 
			PurchaseOrderRef int, GoodsBundleRef int, LoadStationRef int, ProductionRef int, DeliveryRef int, SaleExitRef int,
			UserRef int, AccYear int, DCRef int, DocRef int, Comment nvarchar(255) collate database_default, TrackingNo int, SystemId int,
			DLId int, FifthLedgerId int, SixthLedgerId int, SeventhLedgerId int,
			GoodsRef int, RowOrder float, UnitRef int, UnitCapacity decimal(18, 3), UnitQty decimal(18, 3), TotalQty decimal(18, 3), 
			BatchNoRef int, TICaItmRef int, Tadilltype int, ValuePrice money, VocherItmComment varchar(255), VocherItmDetailComment varchar(255), DetailPrice money )
	*/
	declare @ErrMsg nvarchar(max)='', @VocherItmId int, @ItemCount int, @VocherTypeCode int, @StockDCRef int, @VocherItmDetailId int
	if exists (select *  from #apiVocher
	where VocherTypeCode in(15,65)  
	and StockDCRef=TStockDCRef) 
	begin  
		set @ErrMsg='انبار مبدا و انبار مقصد در این سندها نمی تواند یکسان باشد'
	end 
	if @ErrMsg<>''
	begin
		raiserror (@ErrMsg, 16, 1)
		return
	end
	begin try
		begin tran
		select @VocherTypeCode = VocherTypeCode, @StockDCRef=StockDCRef, @VocherNo=VocherNo from #apiVocher
		if @VocherNo is null
			exec dbo.GetMaxVocherNo @VocherTypeCode, @StockDcRef, @AccYear, @VocherNo output, 0
		else	
			update tblVocherNo set VocherNo=@VocherNo where StockDcRef=@StockDCRef and AccYear=@AccYear and VocherType=@VocherTypeCode
		exec gnr.uspGetNextId 'inv.tblVocherHdr', @VocherId output
		insert into inv.tblVocherHdr(
			Id, VocherNo, StockDCRef, VocherTypeCode, HealthCodeType, HealthCode, VocherDate, TVocherNo, TVocherTypeCode, TStockDCRef,
			SupplierRef, ModifiedDate, ConfirmedBy, ConfirmDate, ReferenceNo, ICAStatus, IsMerge, CustRef, 
			TICAHdrRef, ICAStockDCRef, TVchTypeRef, TadilICAHdrRef, UniqueId, PurchaseOrderRef, GoodsBundleRef, LoadStationRef, 
			ProductionRef, DeliveryRef, SaleExitRef,UserRef, AccYear, DCRef, DocRef, Comment, TrackingNo, SystemId,
			DLId, FifthLedgerId, SixthLedgerId, SeventhLedgerId, Tadilltype)
		select distinct
			@VocherId, @VocherNo, StockDCRef, VocherTypeCode, HealthCodeType, HealthCode, VocherDate, TVocherNo, TVocherTypeCode, TStockDCRef,
			SupplierRef, isnull(ModifiedDate, getdate()) as ModifiedDate, null as ConfirmedBy, null as ConfirmDate, ReferenceNo, ICAStatus, isnull(IsMerge, 0) as IsMerge, CustRef,
			TICAHdrRef, ICAStockDCRef, TVchTypeRef, TadilICAHdrRef, UniqueId, 
			PurchaseOrderRef, GoodsBundleRef, LoadStationRef, ProductionRef, DeliveryRef, SaleExitRef,
			UserRef, AccYear, DCRef, DocRef, Comment, TrackingNo, isnull(SystemId, 1) as SystemId,
			DLId, FifthLedgerId, SixthLedgerId, SeventhLedgerId, Tadilltype
		from #apiVocher
		--select @ItemCount = count(1) from #apiVocher
  --      exec gnr.uspGetNextId 'inv.tblVocherItm', @VocherItmId output, @ItemCount
		insert into inv.tblVocherItm(
			ID, HdrRef, RowOrder, GoodsRef, UnitRef, UnitCapacity, UnitQty, TotalQty, AccYear, TICAItmRef, ValuePrice, Comment)
		select
			NEXT VALUE FOR idgen.tblVocherItm_Sequence
			, @VocherId, min(RowOrder), GoodsRef, UnitRef, UnitCapacity
			, Case when @DontChangeUnitQty=1 then sum(UnitQty) else (sum(TotalQty)/UnitCapacity) end as UnitQty
			, sum(TotalQty), AccYear, TICAItmRef, sum(ValuePrice), VocherItmComment
		from #apiVocher
		group by GoodsRef, UnitRef, UnitCapacity, AccYear, TICAItmRef, VocherItmComment
		--order by RowOrder
		if exists (select 1 from #apiVocher where isnull(BatchNoRef, 0) <> 0)
		begin
			select @ItemCount = count(1) from #apiVocher where isnull(BatchNoRef, 0) <> 0
			--exec gnr.uspGetNextId 'inv.tblvocherItmDetail', @VocherItmDetailId output, @ItemCount
			insert into inv.tblVocherItmDetail(
					ID, ItmRef, BatchNoRef, TotalQty, Comment, Price
				)
			select
				NEXT VALUE FOR idgen.tblVocherItmDetail_Sequence
				, si.Id, ap.BatchNoRef, ap.TotalQty, VocherItmDetailComment, DetailPrice
			from #apiVocher ap
				inner join inv.tblVocherItm si with (nolock) on si.GoodsRef=ap.GoodsRef and si.HdrRef=@VocherId
			where isnull(BatchNoRef, 0) <> 0
			--order by ap.RowOrder
		end
		commit
	end try
	begin catch
		rollback
		set @ErrMsg = error_message()
		raiserror (@ErrMsg, 16, 1)
	end catch
end
GO
