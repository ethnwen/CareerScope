param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = "Stop"
$cs = "Server=localhost;Database=master;Integrated Security=True;TrustServerCertificate=True"
$text = Get-Content -Raw -Path $Path
$batches = [regex]::Split($text, '(?im)^\s*GO\s*$') | Where-Object { $_.Trim() }
$conn = New-Object System.Data.SqlClient.SqlConnection($cs)
$conn.Open()
try {
    foreach ($batch in $batches) {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $batch
        $cmd.CommandTimeout = 0
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($cmd)
        $ds = New-Object System.Data.DataSet
        [void]$adapter.Fill($ds)
        foreach ($t in $ds.Tables) { $t | Format-Table -AutoSize | Out-String | Write-Host }
    }
    Write-Host "Finished: $Path"
}
finally { $conn.Close() }