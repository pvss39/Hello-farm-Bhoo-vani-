$tasks = @('HelloFarmMorning', 'HelloFarmSatellite', 'HelloFarmWeekly')
foreach ($name in $tasks) {
    $task = Get-ScheduledTask -TaskName $name
    $settings = $task.Settings
    $settings.StartWhenAvailable = $true
    $settings.ExecutionTimeLimit = 'PT30M'
    Set-ScheduledTask -TaskName $name -Settings $settings | Out-Null
    Write-Output "Fixed: $name"
}
Write-Output "All tasks will now run after sleep/wake if missed."
