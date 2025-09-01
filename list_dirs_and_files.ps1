# --- Function Definition (Place this at the beginning of your script) ---
function Get-DirectoryTreeString {
    param(
        [string]$Path,
        [string[]]$ExcludeList,
        [string]$Indent = ""
    )

    $treeString = ""

    Get-ChildItem -Path $Path -Directory | ForEach-Object {
        $directory = $_
        $isExcluded = $ExcludeList | Where-Object { (Split-Path $directory.FullName -Parent) -ilike $_ }

        if (-not $isExcluded) {
            $treeString += "$Indent|-- $($directory.Name)`n"
            $treeString += Get-DirectoryTreeString -Path $directory.FullName -ExcludeList $ExcludeList -Indent ($Indent + "|   ")
        }
    }

    Get-ChildItem -Path $Path -File -Exclude $ExcludeList | ForEach-Object {
        $file = $_
        $treeString += "$Indent|-- $($file.Name)`n"
    }
    return $treeString
}

[string[]]$excludeFolderList = @( # Exclusion list
    "*list_dirs_and_files*",
    "*node_modules*",
    "*.git",
    "*.mypy_cache*",
    "*.vscode",
    "*output*",
    "*scripts*",
    "*packaging*",
    "*docs*",
    "*dist*",
    "*\Dev\*",
    "*github*",
    "*clinerules*",
    "*scripts*",
    "*__pycache__*",
    "*build*",
    "*temp*",
    "*.log",
    "*.lock",
    "*.map",
    "*.bak",
    "*.bat",
    "*.temp",
    "*.md",
    "*egg-info*",
    "*.venv*",
    "*.pytest_cache*",
    "*.ruff_cache*",
    "*.ico",
    "*LICENSE",
    "*pnpm-lock.yaml",
    "*package-lock.json",
    "*.DS_Store", # macOS folder metadata file
    "*Thumbs.db",   # Windows thumbnail cache file
    "*docs*"        # Exclude documentation directory
)

$directoryToCrawl = ".\" #  <---  Set your directory path here
$outputFilePath = ".\list_dirs_and_files.txt" # <--- Set output file path

Write-Host "Crawling directory: $($directoryToCrawl)" -ForegroundColor Cyan
Write-Host "Excluding items:" $($excludeFolderList -join ", ") -ForegroundColor Cyan

Write-Host "Generating directory tree..." -ForegroundColor Cyan
$treeOutput = Get-DirectoryTreeString -Path $directoryToCrawl -ExcludeList $excludeFolderList
Write-Host "Directory tree generated." -ForegroundColor Cyan

$outputContent = "" # Initialize variable to store output content

$outputContent += "--- Directory Tree Structure ---`n" # Add tree section header
$outputContent += '```' + "`n" + $treeOutput + "`n" + '```' # Append directory tree string
$outputContent += "`n--- File List and Contents ---`n" # Add file list section header

Get-ChildItem -Path $directoryToCrawl -Recurse -File -Exclude $excludeFolderList | ForEach-Object {
    $allowed = $true
    foreach ($exclude in $excludeFolderList) { 
        if ((Split-Path $_.FullName -Parent) -ilike $exclude) { 
            $allowed = $false
            break
        }
    }
    if ($allowed) {
        Write-Host "Processing file: $($_.FullName)" -ForegroundColor Cyan 
        $outputContent += '```' + "`nFile: $($_.FullName)`n" # Add filename to output content
        $outputContent += (Get-Content -Path $_.FullName) -join "`n" # Add file content
        $outputContent += "`n" + '```' + "`n`n" # Add blank lines between files
    } else {
        Write-Host "Ignoring: $($_.FullName)" -ForegroundColor Gray # Use Write-Verbose for "Ignoring" messages
    }
}

$outputContent | Out-File -FilePath $outputFilePath -Encoding UTF8 # Write accumulated content to file (overwriting) <--- No -Append

Write-Host "Output written to: $($outputFilePath)" -ForegroundColor Cyan 
Write-Host "Run script with -Verbose to see 'Ignoring' messages." -ForegroundColor DarkGray # Inform user about -Verbose

pause