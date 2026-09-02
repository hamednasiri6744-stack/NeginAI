/*
  Staged NeginAI -> Varanegar order bridge (NOT installed by this file).

  Run only after review by the Varanegar DBA, in database NeginPakhsh.
  This script creates no SQL login and contains no password. The application
  login is granted EXECUTE on one wrapper only, never db_datawriter.

  Important numbering rule (verified read-only on 2026-08-23):
  Varanegar keeps the current request number in dbo.tblOrderNo, keyed by
  (SaleOfficeRef, AccYear, DcRef). SLE.tblOrderHdr.OrderNo is not an identity,
  computed column, default, or SQL sequence. dbo.NGT_ReplicateOrderMaster can
  first return the temporary value -OrderHdrRef (the observed pilot returned
  -333013 for OrderHdrRef 333013).

  This wrapper increments exactly one dbo.tblOrderNo row with an update lock,
  replaces that temporary value on the newly-created SLE.tblOrderHdr row, and
  commits the counter, header, TourHistory, and audit atomically. It never uses
  the largest existing header number plus one. Order and price dates come from
  Varanegar's one open sales operation date (dbo.OprDate, SysRef = 1), never
  from the server calendar date. Keep the application feature flags disabled
  until this script has been reviewed and installed by the Varanegar DBA.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

IF DB_NAME() <> N'NeginPakhsh'
    THROW 51000, N'Run this script only in NeginPakhsh.', 1;
IF OBJECT_ID(N'dbo.NGT_ReplicateOrderMaster', N'P') IS NULL
    THROW 51000, N'dbo.NGT_ReplicateOrderMaster was not found.', 1;
IF OBJECT_ID(N'dbo.tblOrderNo', N'U') IS NULL
    THROW 51000, N'dbo.tblOrderNo was not found.', 1;
IF OBJECT_ID(N'SLE.tblOrderHdr', N'U') IS NULL
    THROW 51000, N'SLE.tblOrderHdr was not found.', 1;
IF OBJECT_ID(N'dbo.OprDate', N'V') IS NULL
    THROW 51000, N'dbo.OprDate was not found.', 1;
GO

IF SCHEMA_ID(N'NeginAI') IS NULL EXEC(N'CREATE SCHEMA NeginAI AUTHORIZATION dbo;');
GO

IF OBJECT_ID(N'NeginAI.OrderBridgeAudit', N'U') IS NULL
BEGIN
    CREATE TABLE NeginAI.OrderBridgeAudit
    (
        OrderUniqueId uniqueidentifier NOT NULL PRIMARY KEY,
        RequestedBy nvarchar(128) NOT NULL,
        SystemUsername varchar(50) NOT NULL,
        OrderRef int NOT NULL,
        OrderNo int NOT NULL,
        CreatedAt datetime2(0) NOT NULL
            CONSTRAINT DF_NeginAI_OrderBridgeAudit_CreatedAt DEFAULT SYSUTCDATETIME()
    );
END;
GO

CREATE OR ALTER PROCEDURE NeginAI.usp_SubmitValidatedOrder
    @OrderUniqueId uniqueidentifier,
    @RequestedBy nvarchar(128),
    @SystemUsername varchar(50),
    @PayloadJson nvarchar(max)
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @OrderUniqueId IS NULL OR ISJSON(@PayloadJson) <> 1
        THROW 51001, N'Invalid order contract.', 1;
    IF NULLIF(LTRIM(RTRIM(@RequestedBy)), N'') IS NULL
        THROW 51001, N'RequestedBy is required.', 1;
    IF @SystemUsername <> 'VnAdmin'
        THROW 51001, N'The configured Varanegar system user is not allowed.', 1;

    DECLARE @ExistingOrderRef int, @ExistingOrderNo int, @ExistingUniqueId uniqueidentifier;
    SELECT TOP (1)
        @ExistingOrderRef = V.OrderHdrRef,
        @ExistingOrderNo = H.OrderNo,
        @ExistingUniqueId = H.UniqueId
    FROM dbo.visit_BOOrder AS V
    LEFT JOIN SLE.tblOrderHdr AS H ON H.ID = V.OrderHdrRef
    WHERE V.order_id = @OrderUniqueId;
    IF @ExistingOrderRef IS NOT NULL
    BEGIN
        IF @ExistingOrderNo IS NULL OR @ExistingOrderNo <= 0
            THROW 51007, N'Existing order has no positive final business number.', 1;
        SELECT CAST(1 AS bit) AS Committed, @ExistingOrderRef AS OrderRef,
               @ExistingOrderNo AS OrderNo, @ExistingUniqueId AS OrderUniqueId,
               N'Order already existed; existing result returned.' AS Message;
        RETURN;
    END;

    DECLARE
        @CustomerRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.customer_ref')),
        @DealerRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.dealer_ref')),
        @OrderTypeRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.order_type_ref')),
        @PaymentUsanceRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.payment_usance_ref')),
        @SaleOfficeRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.sale_office_ref')),
        @DcRef int = TRY_CONVERT(int, JSON_VALUE(@PayloadJson, '$.dc_ref')),
        @UserRef int,
        @CustomerUniqueId uniqueidentifier,
        @DealerUniqueId uniqueidentifier,
        @OrderTypeUniqueId uniqueidentifier,
        @PaymentUsanceUniqueId uniqueidentifier,
        @StockUniqueId uniqueidentifier,
        @AccYear int,
        @ErrMsg varchar(8000) = '',
        @ConfirmDate datetime = GETDATE(),
        @SaleOperationDate varchar(10),
        @SaleOperationDateCount int;

    SELECT TOP (1) @UserRef = AppUserId
    FROM dbo.AppUser
    WHERE Username = @SystemUsername AND IsActive = 1 AND ISNULL(IsDeleted, 0) = 0
    ORDER BY AppUserId;
    SELECT @CustomerUniqueId = CustGUID
    FROM GNR.tblCust WHERE ID = @CustomerRef AND Status = 1;
    SELECT TOP (1) @DealerUniqueId = Id
    FROM NGT.Personnels
    WHERE TRY_CONVERT(int, BackOfficeId) = @DealerRef
      AND IsRemoved = 0 AND PersonnelIsActive = 1;
    SELECT @OrderTypeUniqueId = UniqueId
    FROM SLE.tblOrderType WHERE ID = @OrderTypeRef AND Selectable = 1;
    SELECT @PaymentUsanceUniqueId = UniqueId
    FROM GNR.tblPaymentUsance WHERE ID = @PaymentUsanceRef AND Status = 1;

    IF @UserRef IS NULL OR @CustomerUniqueId IS NULL OR @DealerUniqueId IS NULL
       OR @OrderTypeUniqueId IS NULL OR @PaymentUsanceUniqueId IS NULL
       OR @SaleOfficeRef IS NULL OR @DcRef IS NULL
        THROW 51002, N'Header identity or current authorization was not found.', 1;

    DECLARE @Lines TABLE
    (
        RowNo int NOT NULL,
        ProductRef int NOT NULL,
        ProductUniqueId uniqueidentifier NULL,
        StockRef int NOT NULL,
        Qty decimal(18,3) NOT NULL,
        UnitPrice money NOT NULL,
        CPriceRef int NOT NULL,
        AccYear int NOT NULL,
        UnitRef int NOT NULL,
        PayDuration int NOT NULL
    );
    INSERT @Lines
        (RowNo, ProductRef, ProductUniqueId, StockRef, Qty, UnitPrice,
         CPriceRef, AccYear, UnitRef, PayDuration)
    SELECT CONVERT(int, J.[key]) + 1,
           L.ProductRef, L.ProductUniqueId, L.StockRef, L.Qty, L.UnitPrice,
           L.CPriceRef, L.AccYear, L.UnitRef, ISNULL(L.PayDuration, 0)
    FROM OPENJSON(@PayloadJson, '$.lines') AS J
    CROSS APPLY OPENJSON(J.[value])
    WITH
    (
        ProductRef int '$.product_ref',
        ProductUniqueId uniqueidentifier '$.product_unique_id',
        StockRef int '$.stock_ref',
        Qty decimal(18,3) '$.quantity',
        UnitPrice money '$.unit_price',
        CPriceRef int '$.cprice_ref',
        AccYear int '$.acc_year',
        UnitRef int '$.unit_ref',
        PayDuration int '$.pay_duration'
    ) AS L;

    IF NOT EXISTS (SELECT 1 FROM @Lines)
       OR EXISTS (SELECT 1 FROM @Lines WHERE Qty <= 0 OR UnitPrice <= 0)
        THROW 51003, N'Order lines are empty or invalid.', 1;
    IF (SELECT COUNT(DISTINCT StockRef) FROM @Lines) <> 1
       OR (SELECT COUNT(DISTINCT AccYear) FROM @Lines) <> 1
        THROW 51003, N'All lines must use one authorized stock and accounting year.', 1;

    SELECT @AccYear = MIN(AccYear) FROM @Lines;
    SELECT
        @SaleOperationDateCount = COUNT(*),
        @SaleOperationDate = MIN(NULLIF(LTRIM(RTRIM(O.OperationDate)), ''))
    FROM dbo.OprDate AS O
    WHERE O.DCId = @DcRef
      AND O.SysRef = 1
      AND O.AccYearName = @AccYear
      AND O.IsClosed = 0;

    IF @SaleOperationDateCount <> 1 OR @SaleOperationDate IS NULL
        THROW 51008, N'Exactly one open Varanegar sales operation date was not found.', 1;
    IF LEN(@SaleOperationDate) <> 10
       OR @SaleOperationDate NOT LIKE '[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]'
       OR TRY_CONVERT(int, LEFT(@SaleOperationDate, 4)) <> @AccYear
       OR TRY_CONVERT(int, SUBSTRING(@SaleOperationDate, 6, 2)) NOT BETWEEN 1 AND 12
       OR TRY_CONVERT(int, RIGHT(@SaleOperationDate, 2)) NOT BETWEEN 1 AND 31
        THROW 51008, N'Varanegar sales operation date is invalid for the requested accounting year.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM @Lines AS L
        LEFT JOIN GNR.tblGoods AS G
          ON G.ID = L.ProductRef AND G.UniqueId = L.ProductUniqueId
        LEFT JOIN GNR.tblPackage AS P
          ON P.GoodsRef = G.ID AND P.UnitRef = L.UnitRef
         AND P.Qty = 1 AND P.ForSale = 1 AND P.Status = 1
        LEFT JOIN SLE.tblCPrice AS C
          ON C.ID = L.CPriceRef AND C.GoodsRef = G.ID
         AND C.UnitRef = L.UnitRef AND C.SalePrice = L.UnitPrice
         AND @SaleOperationDate BETWEEN C.StartDate
                                    AND ISNULL(NULLIF(C.EndDate, ''), @SaleOperationDate)
        WHERE G.ID IS NULL OR P.ID IS NULL OR C.ID IS NULL
    )
        THROW 51004, N'Product, base package, or exact current contract price did not match Varanegar.', 1;

    SELECT @StockUniqueId = S.UniqueId
    FROM GNR.tblStockDC AS S
    WHERE S.ID = (SELECT TOP (1) StockRef FROM @Lines) AND S.DCRef = @DcRef;
    IF @StockUniqueId IS NULL OR NOT EXISTS
       (SELECT 1 FROM GNR.tblStockGoods
        WHERE StockDCRef = (SELECT TOP (1) StockRef FROM @Lines)
          AND AccYear = @AccYear)
        THROW 51005, N'Stock or accounting year is not valid for this DC.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- The official replication procedure delegates discount, addition,
        -- tax and credit checks to the Varanegar EVC procedures. Those
        -- procedures use the same caller-scoped temp-table contract as
        -- dbo.NGT_ReplicateTour, so the complete contract must exist before
        -- NGT_ReplicateOrderMaster is invoked.
        CREATE TABLE #tblTempEvc
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            RefID int NULL,
            DateOf varchar(10) COLLATE DATABASE_DEFAULT NULL,
            PayType int NULL,
            AccYear int NULL,
            DCRef int NULL,
            CustRef int NULL,
            DisType int NULL,
            EVCType int NULL,
            OrderType int NULL,
            StockDCRef int NULL,
            DCSaleOfficeRef int NULL,
            Dis1 money NULL,
            Dis2 money NULL,
            Dis3 money NULL,
            Add1 money NULL,
            Add2 money NULL,
            DealerRef int NULL,
            OprDate varchar(10) COLLATE DATABASE_DEFAULT NULL,
            Tax money NULL,
            Charge money NULL,
            PaymentUsanceRef int NULL,
            OtherDiscount money NULL,
            OtherAddition money NULL,
            EvcCalcStepType int NULL
        );
        CREATE TABLE #tblTempEvcItem
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EVCRef int NULL,
            RowOrder real NULL,
            GoodsRef int NULL,
            UnitQty decimal(18,3) NULL,
            CPriceRef int NULL,
            AccYear int NULL,
            UnitRef int NULL,
            UnitCapasity decimal(18,3) NULL,
            TotalQty decimal(18,3) NULL,
            AmountNut money NULL,
            Discount money NULL,
            Amount money NULL,
            PrizeType bit NULL,
            SupAmount money NULL,
            AddAmount money NULL,
            UserPrice money NULL,
            CustPrice money NULL,
            PriceRef int NULL,
            DisRef int NULL,
            Tax money NULL DEFAULT (0),
            Charge money NULL DEFAULT (0),
            TaxPercent decimal(18,3) NULL DEFAULT (0),
            ChargePercent decimal(18,3) NULL DEFAULT (0),
            PeriodicDiscountRef int NOT NULL DEFAULT (0),
            FreeReasonId int NULL,
            EvcItemDis1 money NULL,
            EvcItemDis2 money NULL,
            EvcItemDis3 money NULL,
            EvcItemAdd1 money NULL,
            EvcItemAdd2 money NULL,
            EvcItemOtherDiscount money NULL,
            EvcItemOtherAddition money NULL,
            UsanceDay int NULL
        );
        CREATE TABLE #tblTempEvcItemStatutes
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EVCItemRef int NULL,
            RowOrder real NULL,
            DisRef int NULL,
            DisGroup int NULL,
            Discount money NULL,
            AddAmount money NULL,
            SupAmount money NULL
        );
        CREATE TABLE #tblTempEvcSkipDiscount
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EvcRef int NULL,
            SaleRef int NULL,
            DisRef int NULL,
            SkipGoodsRef int NULL
        );
        CREATE TABLE #tblTempEvcPrize
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EvcRef int NOT NULL,
            DiscountRef int NOT NULL,
            GoodsRef int NOT NULL,
            PrizeQty int NOT NULL,
            QtyUnit int NULL,
            OrderDiscountRef int NULL
        );
        CREATE TABLE #tblTempEvcPeriodicDiscount
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EvcRef int NULL,
            PeriodicDiscountRef int NULL,
            DiscountAmount money NULL,
            PaymentRef int NULL
        );
        CREATE TABLE #tblTempEvcPrizePackage
        (
            ID int IDENTITY(1398,1) NOT NULL PRIMARY KEY,
            EvcRef int NULL,
            DiscountRef int NULL,
            MainGoodsPackageItemRef int NULL,
            ReplaceGoodsPackageItemRef int NULL,
            PrizeCount int NULL,
            PrizeQty int NULL,
            PrizeRef int NULL
        );

        CREATE TABLE #TourMetaData
        (
            PreviewOrderMode bit NOT NULL,
            HostName varchar(100) NULL,
            TourId uniqueidentifier NULL
        );
        INSERT #TourMetaData VALUES (0, 'NeginAI-OrderBridge', NULL);

        CREATE TABLE #TourExtraData
        (
            CustomerUniqueId uniqueidentifier NOT NULL,
            RoleCode varchar(250) NULL
        );
        INSERT #TourExtraData SELECT @CustomerUniqueId, NULL;

        CREATE TABLE #CallOrder
        (
            CallOrderUniqueId uniqueidentifier NOT NULL,
            OrderDate varchar(10) NOT NULL,
            CustRef uniqueidentifier NOT NULL,
            DealerRef uniqueidentifier NOT NULL,
            ShipDate varchar(10) NULL,
            PaymentUsanceRef uniqueidentifier NOT NULL,
            Comment nvarchar(2000) NULL,
            OrderTypeRef uniqueidentifier NOT NULL,
            PriceClassVnLiteUniqueId uniqueidentifier NULL,
            IsConflictVoucher bit NOT NULL,
            OrderOtherRoundDiscount money NOT NULL,
            DistributionUniqueId uniqueidentifier NULL,
            StockUniqueId uniqueidentifier NULL
        );
        INSERT #CallOrder VALUES
        (@OrderUniqueId, @SaleOperationDate, @CustomerUniqueId, @DealerUniqueId,
         @SaleOperationDate,
         @PaymentUsanceUniqueId, N'NeginAI validated order', @OrderTypeUniqueId,
         NULL, 0, 0, NULL, @StockUniqueId);

        CREATE TABLE #LineItem
        (
            OrderLineUniqueId uniqueidentifier NOT NULL,
            CallOrderUniqueId uniqueidentifier NOT NULL,
            ProductUniqueId uniqueidentifier NOT NULL,
            PackageUniqueId uniqueidentifier NOT NULL,
            Qty decimal(18,3) NOT NULL,
            FreeReasonId uniqueidentifier NULL,
            CPriceUniqueId uniqueidentifier NULL,
            StockDCRef uniqueidentifier NOT NULL,
            UnitPrice money NOT NULL,
            RowIndex int NOT NULL,
            PayDuration int NOT NULL,
            PayDisRef int NULL,
            IsPackage bit NOT NULL,
            Description nvarchar(2000) NULL,
            StockUniqueId uniqueidentifier NULL,
            UnitRef int NULL,
            FreeReasonRef int NULL
        );
        INSERT #LineItem
        (
            OrderLineUniqueId, CallOrderUniqueId, ProductUniqueId, PackageUniqueId,
            Qty, FreeReasonId, CPriceUniqueId, StockDCRef, UnitPrice, RowIndex,
            PayDuration, PayDisRef, IsPackage, Description, StockUniqueId, UnitRef,
            FreeReasonRef
        )
        SELECT NEWID(), @OrderUniqueId, G.UniqueId, P.UniqueId,
               L.Qty, NULL, C.UniqueId, @StockUniqueId, L.UnitPrice, L.RowNo,
               L.PayDuration, NULL, 0, N'', @StockUniqueId, L.UnitRef, NULL
        FROM @Lines AS L
        INNER JOIN GNR.tblGoods AS G ON G.ID = L.ProductRef
        CROSS APPLY
        (
            SELECT TOP (1) Package.UniqueId
            FROM GNR.tblPackage AS Package
            WHERE Package.GoodsRef = G.ID AND Package.UnitRef = L.UnitRef
              AND Package.Qty = 1 AND Package.ForSale = 1 AND Package.Status = 1
            ORDER BY Package.DefaultForSale DESC, Package.ID
        ) AS P
        INNER JOIN SLE.tblCPrice AS C ON C.ID = L.CPriceRef;

        CREATE TABLE #BatchItem
        (
            OrderLineUniqueId uniqueidentifier NULL,
            CallOrderUniqueId uniqueidentifier NULL,
            BatchRef int NULL,
            BatchNoRef int NULL,
            Qty decimal(18,3) NULL,
            PaymentUsanceDay int NULL
        );
        CREATE TABLE #CallOrderPrize
        (
            CallOrderUniqueId uniqueidentifier NULL,
            ProductUniqueId uniqueidentifier NULL,
            UnitRef int NULL,
            FreeReasonId uniqueidentifier NULL,
            TotalQty decimal(18,3) NULL,
            StockUniqueId uniqueidentifier NULL
        );
        CREATE TABLE #FinalResult
        (
            EntityUniqueId uniqueidentifier,
            BackOfficeUniqueId uniqueidentifier,
            BackOfficeRef int,
            CustomerId int,
            [Date] varchar(10),
            BackOfficeNo varchar(50),
            [Type] int
        );
        CREATE TABLE #TableErrMsg (ErrNumber int, ErrorMessage varchar(max));

        EXEC dbo.NGT_ReplicateOrderMaster
            @userRef = @UserRef,
            @CustomerPathId = NULL,
            @AlternateStockId = NULL,
            @DcRef = @DcRef,
            @AccYear = @AccYear,
            @ErrMsg = @ErrMsg OUTPUT,
            @IgnoreOnHandQty = 0,
            @ConfirmUserId = @UserRef,
            @ConfirmDate = @ConfirmDate,
            @CreateSaleWithOrder = 0;

        IF NULLIF(LTRIM(RTRIM(@ErrMsg)), '') IS NOT NULL
            THROW 51006, @ErrMsg, 1;
        IF NOT EXISTS (SELECT 1 FROM #FinalResult WHERE [Type] = 1)
            THROW 51006, N'Varanegar returned no committed order result.', 1;

        SELECT TOP (1)
            @ExistingOrderRef = BackOfficeRef,
            @ExistingOrderNo = TRY_CONVERT(int, BackOfficeNo),
            @ExistingUniqueId = BackOfficeUniqueId
        FROM #FinalResult
        WHERE [Type] = 1;

        IF @ExistingOrderRef IS NULL OR @ExistingUniqueId IS NULL
            THROW 51007, N'Varanegar did not return the created order identity.', 1;

        DECLARE
            @HeaderOrderNo int,
            @HeaderAccYear int,
            @HeaderDcRef int,
            @AllocatedOrderNo int;

        SELECT
            @HeaderOrderNo = H.OrderNo,
            @HeaderAccYear = H.AccYear,
            @HeaderDcRef = H.DCRef
        FROM SLE.tblOrderHdr AS H WITH (UPDLOCK, HOLDLOCK)
        WHERE H.ID = @ExistingOrderRef
          AND H.UniqueId = @ExistingUniqueId;

        IF @HeaderOrderNo IS NULL
            THROW 51007, N'The created Varanegar order header was not found.', 1;
        IF @HeaderAccYear <> @AccYear OR @HeaderDcRef <> @DcRef
            THROW 51007, N'The created order year or DC does not match the validated contract.', 1;

        IF @HeaderOrderNo <= 0
        BEGIN
            -- The low-level replication contract uses -OrderHdrRef only as a
            -- temporary value. Do not rewrite any other unexpected number.
            IF @HeaderOrderNo <> -@ExistingOrderRef
                THROW 51007, N'Unexpected temporary Varanegar order number.', 1;

            DECLARE @Allocated TABLE (OrderNo int NOT NULL);
            UPDATE dbo.tblOrderNo WITH (UPDLOCK, HOLDLOCK)
               SET OrderNo = ISNULL(OrderNo, 0) + 1
               OUTPUT inserted.OrderNo INTO @Allocated (OrderNo)
             WHERE SaleOfficeRef = @SaleOfficeRef
               AND AccYear = @AccYear
               AND DcRef = @DcRef;

            IF @@ROWCOUNT <> 1
                THROW 51007, N'Exactly one Varanegar order counter row was not found.', 1;
            SELECT @AllocatedOrderNo = OrderNo FROM @Allocated;
            IF @AllocatedOrderNo IS NULL OR @AllocatedOrderNo <= 0
                THROW 51007, N'Varanegar allocated an invalid request number.', 1;
            IF EXISTS
            (
                SELECT 1
                FROM SLE.tblOrderHdr AS H WITH (UPDLOCK, HOLDLOCK)
                WHERE H.ID <> @ExistingOrderRef
                  AND H.AccYear = @AccYear
                  AND H.DCRef = @DcRef
                  AND H.OrderNo = @AllocatedOrderNo
            )
                THROW 51007, N'The allocated Varanegar request number already exists.', 1;

            UPDATE SLE.tblOrderHdr
               SET OrderNo = @AllocatedOrderNo
             WHERE ID = @ExistingOrderRef
               AND UniqueId = @ExistingUniqueId
               AND OrderNo = @HeaderOrderNo;
            IF @@ROWCOUNT <> 1
                THROW 51007, N'The temporary Varanegar request number changed concurrently.', 1;

            SET @ExistingOrderNo = @AllocatedOrderNo;
            UPDATE #FinalResult
               SET BackOfficeNo = CONVERT(varchar(50), @ExistingOrderNo)
             WHERE [Type] = 1 AND BackOfficeRef = @ExistingOrderRef;
        END
        ELSE
            SET @ExistingOrderNo = @HeaderOrderNo;

        IF @ExistingOrderNo IS NULL OR @ExistingOrderNo <= 0
            THROW 51007, N'Positive Varanegar request numbering did not complete.', 1;

        INSERT dbo.TourHistory
            (EntityUniqueId, BackOfficeUniqueId, BackOfficeRef, CustomerId,
             [Date], BackOfficeNo, [Type], CreatedDate)
        SELECT EntityUniqueId, BackOfficeUniqueId, BackOfficeRef, CustomerId,
               [Date], TRY_CONVERT(int, BackOfficeNo), [Type], GETDATE()
        FROM #FinalResult AS R
        WHERE R.[Type] = 1
          AND NOT EXISTS
              (SELECT 1 FROM dbo.TourHistory AS H
               WHERE H.EntityUniqueId = R.EntityUniqueId AND H.[Type] = 1);

        INSERT NeginAI.OrderBridgeAudit
            (OrderUniqueId, RequestedBy, SystemUsername, OrderRef, OrderNo)
        VALUES
            (@OrderUniqueId, @RequestedBy, @SystemUsername,
             @ExistingOrderRef, @ExistingOrderNo);

        COMMIT TRANSACTION;
        SELECT CAST(1 AS bit) AS Committed, @ExistingOrderRef AS OrderRef,
               @ExistingOrderNo AS OrderNo, @ExistingUniqueId AS OrderUniqueId,
               N'Order registered with an official positive Varanegar number.' AS Message;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

IF DATABASE_PRINCIPAL_ID(N'neginai_order_executor') IS NULL
    CREATE ROLE neginai_order_executor AUTHORIZATION dbo;
GO
GRANT EXECUTE ON OBJECT::NeginAI.usp_SubmitValidatedOrder TO neginai_order_executor;
DENY SELECT, INSERT, UPDATE, DELETE TO neginai_order_executor;
GO

/* DBA-only provisioning example (choose a strong secret outside this file):
   CREATE LOGIN [neginai_order_app] WITH PASSWORD = '<set-out-of-band>';
   CREATE USER [neginai_order_app] FOR LOGIN [neginai_order_app];
   ALTER ROLE [neginai_order_executor] ADD MEMBER [neginai_order_app];
*/
