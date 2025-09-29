# Load environment variables from .env file into azd environment
# Run this script before azd up

$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            azd env set $name $value
            Write-Host "Set environment variable: $name"
        }
    }
    Write-Host "All environment variables loaded from .env file"
} else {
    Write-Host "Error: .env file not found. Please copy .env.template to .env and fill in your values."
    exit 1
}
