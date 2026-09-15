# Explicit local diagnostic only. Never calls production or changes source DB.
# Clone contains native modules/triggers and limited snapshot data, not a full restore.
param([switch]$Create,[switch]$Seed,[switch]$Opening)
$ErrorActionPreference='Stop'
$master=New-Object System.Data.SqlClient.SqlConnection 'Server=127.0.0.1;Database=master;Integrated Security=True;Connect Timeout=5;Application Name=NeginAI isolated interwarehouse test'
$source=New-Object System.Data.SqlClient.SqlConnection 'Server=127.0.0.1;Database=NeginPakhsh_WebDev;Integrated Security=True;Connect Timeout=5;Application Name=NeginAI isolated interwarehouse test'
$target=New-Object System.Data.SqlClient.SqlConnection 'Server=127.0.0.1;Database=NeginAI_InterwarehouseBridge_Test;Integrated Security=True;Connect Timeout=5;Application Name=NeginAI isolated interwarehouse test'
try {
 $master.Open()
 if($Create) {
  $cmd=$master.CreateCommand();$cmd.CommandTimeout=180
  $cmd.CommandText="IF DB_ID('NeginAI_InterwarehouseBridge_Test') IS NOT NULL THROW 51550,'Refuse existing database.',1; IF DATABASEPROPERTYEX('NeginPakhsh_WebDev','Updateability')<>'READ_ONLY' THROW 51550,'Source must remain read only.',1; DBCC CLONEDATABASE(NeginPakhsh_WebDev,NeginAI_InterwarehouseBridge_Test) WITH NO_STATISTICS,NO_QUERYSTORE; ALTER DATABASE NeginAI_InterwarehouseBridge_Test SET READ_WRITE;"
  $null=$cmd.ExecuteNonQuery()
 }
 $target.Open();$source.Open()
 $guard=$target.CreateCommand();$guard.CommandText="IF DB_NAME()<>'NeginAI_InterwarehouseBridge_Test' OR DATABASEPROPERTYEX(DB_NAME(),'IsClone')<>1 THROW 51550,'Unexpected fixture target.',1;"
 $null=$guard.ExecuteNonQuery()
 if($Seed) {
  $fixtures=[ordered]@{
   'dbo.AppUser'='AppUserId=1'; 'GNR.tblDC'='ID=1';
   'GNR.tblStockDC'='ID IN(1,2,9)'; 'GNR.tblGoods'='ID=4665';
   'GNR.tblPackage'='GoodsRef=4665'; 'GNR.tblStockGoods'='GoodsRef=4665 AND StockDCRef IN(1,2,9) AND AccYear=1405';
   'GNR.tblServerConfig'='1=1'; 'GNR.tblGeneralConfig'='1=1';
   'dbo.tblSite'='1=1';'dbo.tblSiteInfo'='1=1';'dbo.tblSiteInfoDetail'='DCRef=1';
   'GNR.tblAccYear'='AccYear=1405'; 'GNR.tblOprDate'='AccYear=1405 AND DCRef=1 AND SysRef=1';
   'GNR.tblLookup'='1=1'; 'inv.tblCardexType'='1=1'
  }
  foreach($tableName in $fixtures.Keys) {
   $check=$target.CreateCommand();$check.CommandText="SELECT COUNT(*) FROM $tableName"
   if([int]$check.ExecuteScalar() -ne 0){throw "Refuse already seeded table $tableName"}
   $cmd=$source.CreateCommand();$cmd.CommandText="SELECT * FROM $tableName WHERE "+$fixtures[$tableName]
   $adapter=New-Object System.Data.SqlClient.SqlDataAdapter $cmd
   $data=New-Object System.Data.DataTable;$null=$adapter.Fill($data)
   # Snapshot import only: normal subsequent bridge calls run all native triggers.
   $bulk=New-Object System.Data.SqlClient.SqlBulkCopy($target,[System.Data.SqlClient.SqlBulkCopyOptions]::KeepIdentity,$null)
   try {
    $bulk.DestinationTableName=$tableName
    $meta=$source.CreateCommand();$meta.CommandText="SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(@table) AND is_computed=0 AND system_type_id<>189"
    $null=$meta.Parameters.AddWithValue('@table',$tableName);$reader=$meta.ExecuteReader()
    try{while($reader.Read()){$null=$bulk.ColumnMappings.Add($reader.GetString(0),$reader.GetString(0))}}finally{$reader.Close()}
    $bulk.WriteToServer($data);Write-Output "$tableName : $($data.Rows.Count) rows"
   }finally{$bulk.Close();$data.Dispose();$adapter.Dispose()}
  }
  $mark=$target.CreateCommand();$mark.CommandText="EXEC sys.sp_addextendedproperty @name=N'NeginAI_IsolatedInterwarehouseTest',@value=1;"
  $null=$mark.ExecuteNonQuery()
 }
 if($Opening) {
  # Artificial opening balance only in this owned diagnostic clone. Native
  # cardex validation remains enabled; do not bypass it with negative-stock flags.
  $check=$target.CreateCommand();$check.CommandText='SELECT COUNT(*) FROM inv.tblVocherHdr'
  if([int]$check.ExecuteScalar() -ne 0){throw 'Refuse opening fixture on nonempty voucher history'}
  foreach($tableName in @('inv.tblVocherHdr','inv.tblVocherItm')) {
   $cmd=$source.CreateCommand()
   $cmd.CommandText=if($tableName -eq 'inv.tblVocherHdr'){
    "SELECT TOP(1) H.* FROM inv.tblVocherHdr H JOIN inv.tblVocherItm I ON I.HdrRef=H.ID WHERE I.GoodsRef=4665 AND H.StockDCRef=2 AND H.VocherTypeCode=20 AND H.AccYear=1405 ORDER BY H.ID"
   }else{
    "SELECT TOP(1) I.* FROM inv.tblVocherHdr H JOIN inv.tblVocherItm I ON I.HdrRef=H.ID WHERE I.GoodsRef=4665 AND H.StockDCRef=2 AND H.VocherTypeCode=20 AND H.AccYear=1405 ORDER BY H.ID"
   }
   $adapter=New-Object System.Data.SqlClient.SqlDataAdapter $cmd;$data=New-Object System.Data.DataTable;$null=$adapter.Fill($data)
   if($data.Rows.Count -ne 1){throw 'Opening source fixture missing'}
   $data.Rows[0]['ID']=2000000001
   if($tableName -eq 'inv.tblVocherHdr'){
    $data.Rows[0]['VocherNo']=2000000001;$data.Rows[0]['VocherDate']='1405/01/01'
    $data.Rows[0]['Comment']='ISOLATED SYNTHETIC OPENING FIXTURE';$data.Rows[0]['ConfirmedBy']=1
    $data.Rows[0]['ConfirmDate']=[DateTime]::Parse('2026-03-21')
   }else{
    $data.Rows[0]['HdrRef']=2000000001;$data.Rows[0]['TotalQty']=290
    $data.Rows[0]['UnitCapacity']=1;$data.Rows[0]['UnitQty']=290
   }
   $bulk=New-Object System.Data.SqlClient.SqlBulkCopy($target,[System.Data.SqlClient.SqlBulkCopyOptions]::KeepIdentity,$null)
   try{
    $bulk.DestinationTableName=$tableName;$meta=$source.CreateCommand()
    $meta.CommandText="SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(@table) AND is_computed=0 AND system_type_id<>189"
    $null=$meta.Parameters.AddWithValue('@table',$tableName);$reader=$meta.ExecuteReader()
    try{while($reader.Read()){$null=$bulk.ColumnMappings.Add($reader.GetString(0),$reader.GetString(0))}}finally{$reader.Close()}
    $bulk.WriteToServer($data);Write-Output "$tableName : one artificial opening fixture"
   }finally{$bulk.Close();$data.Dispose();$adapter.Dispose()}
  }
 }
}finally{$master.Close();$target.Close();$source.Close()}
