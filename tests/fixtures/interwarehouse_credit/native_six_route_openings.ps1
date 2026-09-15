# Extend only the retained, owned native diagnostic clone's artificial opening
# cardex fixtures. Does not change stock balances or disable native triggers.
$ErrorActionPreference='Stop'
$db=New-Object System.Data.SqlClient.SqlConnection 'Server=127.0.0.1;Database=NeginAI_InterwarehouseBridge_Test;Integrated Security=True;Connect Timeout=5;Application Name=NeginAI isolated six-route fixture'
$db.Open()
try {
 $guard=$db.CreateCommand()
 $guard.CommandText="IF DB_NAME()<>'NeginAI_InterwarehouseBridge_Test' OR DATABASEPROPERTYEX(DB_NAME(),'IsClone')<>1 OR NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=0 AND name='NeginAI_IsolatedInterwarehouseTest' AND CONVERT(int,value)=1) THROW 51550,'Unexpected clone.',1; IF EXISTS(SELECT 1 FROM NeginAI.InterwarehouseCreditPolicy WHERE Enabled=1 OR IsolatedValidationComplete=1) THROW 51550,'Tests must be inactive during fixture load.',1; IF NOT EXISTS(SELECT 1 FROM inv.tblVocherHdr WHERE ID=2000000001 AND VocherTypeCode=20 AND StockDCRef=2 AND Comment='ISOLATED SYNTHETIC OPENING FIXTURE') THROW 51550,'Missing original opening fixture.',1;"
 $null=$guard.ExecuteNonQuery()
 foreach($routeStock in @(1,9)) {
  $fixtureId=2000000010+$routeStock
  $check=$db.CreateCommand();$check.CommandText="SELECT COUNT(*) FROM inv.tblVocherHdr WHERE StockDCRef=$routeStock OR ID=$fixtureId"
  if([int]$check.ExecuteScalar() -ne 0){throw "Refuse nonempty stock voucher fixture $routeStock"}
  $check.CommandText="SELECT OnHandQty FROM gnr.tblStockGoods WHERE StockDCRef=$routeStock AND GoodsRef=4665 AND AccYear=1405"
  $fixtureQty=[decimal]$check.ExecuteScalar()
  if(($routeStock -eq 1 -and $fixtureQty -ne 481) -or ($routeStock -eq 9 -and $fixtureQty -ne 497)){throw 'Unexpected starting stock fixture'}
  $tables=@{}
  foreach($tableName in @('inv.tblVocherHdr','inv.tblVocherItm')) {
   $cmd=$db.CreateCommand();$cmd.CommandText="SELECT * FROM $tableName WHERE ID=2000000001"
   $adapter=New-Object System.Data.SqlClient.SqlDataAdapter $cmd;$data=New-Object System.Data.DataTable;$null=$adapter.Fill($data)
   if($data.Rows.Count -ne 1){throw 'Unexpected original fixture row count'}
   $data.Rows[0]['ID']=$fixtureId
   if($tableName -eq 'inv.tblVocherHdr'){
    $data.Rows[0]['StockDCRef']=$routeStock;$data.Rows[0]['VocherNo']=$fixtureId
    $data.Rows[0]['UniqueId']=[DBNull]::Value
   }else{
    $data.Rows[0]['HdrRef']=$fixtureId;$data.Rows[0]['TotalQty']=$fixtureQty
    $data.Rows[0]['UnitQty']=$fixtureQty;$data.Rows[0]['UnitCapacity']=1
   }
   $tables[$tableName]=$data;$adapter.Dispose()
  }
  $tx=$db.BeginTransaction()
  try {
   foreach($tableName in @('inv.tblVocherHdr','inv.tblVocherItm')) {
    $bulk=New-Object System.Data.SqlClient.SqlBulkCopy($db,[System.Data.SqlClient.SqlBulkCopyOptions]::KeepIdentity,$tx)
    try {
     $bulk.DestinationTableName=$tableName;$meta=$db.CreateCommand();$meta.Transaction=$tx
     $meta.CommandText="SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(@table) AND is_computed=0 AND system_type_id<>189"
     $null=$meta.Parameters.AddWithValue('@table',$tableName);$reader=$meta.ExecuteReader()
     try{while($reader.Read()){$null=$bulk.ColumnMappings.Add($reader.GetString(0),$reader.GetString(0))}}finally{$reader.Close()}
     $bulk.WriteToServer($tables[$tableName])
    }finally{$bulk.Close();$tables[$tableName].Dispose()}
   }
   $tx.Commit();Write-Output "Opening cardex fixture stock $routeStock quantity $fixtureQty; physical stock unchanged"
  }catch{$tx.Rollback();throw}
 }
}finally{$db.Close()}
