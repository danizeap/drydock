# Thin Windows wrapper. All logic lives in scripts/sdd.py (cross-platform).
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$script = Join-Path $PSScriptRoot "sdd.py"
# Translate legacy -Force switch to --force; @() keeps a single arg an array
# (a scalar would splat as individual characters).
$translated = @($Rest | ForEach-Object { if ($_ -eq "-Force") { "--force" } else { $_ } })
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py $script @translated
exit $LASTEXITCODE
