# PowerShell script for Windows
# Generic team setup script to be placed in each team's folder (output/team_X/)
# This script automatically detects which team it belongs to and sets up multi-login SSH configuration

# Get the current directory name to determine team number
$CURRENT_DIR = Split-Path -Path (Get-Location) -Leaf
$TEAM_NAME = $CURRENT_DIR

Write-Host "Setting up multi-login SSH configuration for $TEAM_NAME..."

# Variables
$CREDENTIALS_FILE = "${TEAM_NAME}_credentials.csv"
$IPS_FILE = "${TEAM_NAME}_ips.csv"
$S3_BUCKET = "distributed-systems-course-team-keys-4cdcfb7e4d04685bbd448e40d9"
$KEY_PATH = "$env:USERPROFILE\.ssh\team_key.pem"
$SSH_CONFIG_PATH = "$env:USERPROFILE\.ssh\config"

# Step 1: Check if required files exist
Write-Host "Step 1: Checking for required files..."
if (-not (Test-Path $CREDENTIALS_FILE)) {
    Write-Host "Error: Credentials file not found at $CREDENTIALS_FILE" -ForegroundColor Red
    Write-Host "Make sure you're running this script from your team folder." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $IPS_FILE)) {
    Write-Host "Error: IPs file not found at $IPS_FILE" -ForegroundColor Red
    Write-Host "Make sure you're running this script from your team folder." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "team_guide.pdf")) {
    Write-Host "Warning: team_guide.pdf not found in the current directory." -ForegroundColor Yellow
    Write-Host "You may want to review the guide for complete instructions." -ForegroundColor Yellow
}

Write-Host "Required files found."

# Step 2: Configure AWS CLI with team credentials
Write-Host "Step 2: Configuring AWS CLI with $TEAM_NAME credentials..."
# Extract credentials from CSV file (skip header line)
$credentials = Import-Csv $CREDENTIALS_FILE
$ACCESS_KEY = $credentials[-1].access_key_id
$SECRET_KEY = $credentials[-1].secret_access_key

if ([string]::IsNullOrEmpty($ACCESS_KEY) -or [string]::IsNullOrEmpty($SECRET_KEY)) {
    Write-Host "Error: Could not extract access key or secret key from credentials file." -ForegroundColor Red
    exit 1
}

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version
    Write-Host "AWS CLI is installed: $awsVersion"
} catch {
    Write-Host "AWS CLI is not installed. Installing instructions:" -ForegroundColor Red
    Write-Host "Windows: Download from AWS website (https://aws.amazon.com/cli/)" -ForegroundColor Yellow
    Write-Host "Please install AWS CLI and run this script again." -ForegroundColor Yellow
    exit 1
}

# Create AWS credentials file
$awsFolder = "$env:USERPROFILE\.aws"
if (-not (Test-Path $awsFolder)) {
    New-Item -ItemType Directory -Path $awsFolder | Out-Null
}

@"
[default]
aws_access_key_id = $ACCESS_KEY
aws_secret_access_key = $SECRET_KEY
"@ | Out-File -FilePath "$awsFolder\credentials" -Encoding utf8

# Create AWS config file
@"
[default]
region = eu-central-1
output = json
"@ | Out-File -FilePath "$awsFolder\config" -Encoding utf8

Write-Host "AWS CLI configured successfully."

# Step 3: Download the private SSH key
Write-Host "Step 3: Downloading private SSH key..."
$sshFolder = "$env:USERPROFILE\.ssh"
if (-not (Test-Path $sshFolder)) {
    New-Item -ItemType Directory -Path $sshFolder | Out-Null
}

try {
    aws s3 cp "s3://$S3_BUCKET/$TEAM_NAME/private_key.pem" $KEY_PATH 2>$null
    Write-Host "Private key downloaded successfully."
    
    # Set appropriate permissions for the key file
    # In Windows, we need to use icacls to set permissions
    icacls $KEY_PATH /inheritance:r
    icacls $KEY_PATH /grant:r "$($env:USERNAME):(R)"
    Write-Host "Key permissions set to read-only for current user."
    $keyDownloaded = $true
} catch {
    Write-Host "Error: Could not download private key from S3 bucket." -ForegroundColor Red
    Write-Host "This could be due to:" -ForegroundColor Yellow
    Write-Host "1. The S3 bucket doesn't exist or has a different name." -ForegroundColor Yellow
    Write-Host "2. The credentials don't have permission to access the bucket." -ForegroundColor Yellow
    Write-Host "3. The private key file doesn't exist in the expected location." -ForegroundColor Yellow
    Write-Host "4. Network connectivity issues." -ForegroundColor Yellow
    
    # Check if we can list the bucket
    Write-Host "Checking if we can access the S3 bucket..."
    try {
        aws s3 ls "s3://$S3_BUCKET" 2>$null
        Write-Host "S3 bucket is accessible. Checking for the private key file..."
        try {
            aws s3 ls "s3://$S3_BUCKET/$TEAM_NAME/" 2>$null
            Write-Host "Team directory exists in the bucket. Listing contents:"
            aws s3 ls "s3://$S3_BUCKET/$TEAM_NAME/"
        } catch {
            Write-Host "Team directory doesn't exist or is not accessible." -ForegroundColor Red
        }
    } catch {
        Write-Host "Cannot access the S3 bucket. Check your credentials and permissions." -ForegroundColor Red
    }
    $keyDownloaded = $false
}

# Step 4: Extract IPs for connection
Write-Host "Step 4: Extracting connection information..."
# Extract IPs from CSV file
$ips = Import-Csv $IPS_FILE
$PUBLIC_IP = $ips[-1].public_ip
$PRIVATE_IPS = @()

# Get all columns except the first two (assuming they are team_name and public_ip)
$ipProperties = $ips[-1].PSObject.Properties | Where-Object { $_.Name -ne "team_name" -and $_.Name -ne "public_ip" }
foreach ($prop in $ipProperties) {
    if (-not [string]::IsNullOrWhiteSpace($prop.Value)) {
        $PRIVATE_IPS += $prop.Value.Trim()
    }
}

if ([string]::IsNullOrEmpty($PUBLIC_IP)) {
    Write-Host "Error: Could not extract public IP from IPs file." -ForegroundColor Red
    exit 1
}

# Step 5: Set up SSH config for easier connections
Write-Host "Step 5: Setting up SSH config for easier connections..."
# Create or append to SSH config file
if (-not (Test-Path $SSH_CONFIG_PATH)) {
    New-Item -ItemType File -Path $SSH_CONFIG_PATH | Out-Null
}

# Add bastion host config
@"

# $TEAM_NAME Bastion Host
Host ${TEAM_NAME}-bastion
    HostName $PUBLIC_IP
    User ubuntu
    IdentityFile $KEY_PATH
    StrictHostKeyChecking no

"@ | Out-File -FilePath $SSH_CONFIG_PATH -Append -Encoding utf8

# Add private VM configs
$VM_COUNT = 1
foreach ($IP in $PRIVATE_IPS) {
    if (-not [string]::IsNullOrWhiteSpace($IP)) {
        @"
# $TEAM_NAME VM $VM_COUNT
Host ${TEAM_NAME}-vm$VM_COUNT
    HostName $IP
    User ubuntu
    IdentityFile $KEY_PATH
    ProxyJump ${TEAM_NAME}-bastion
    StrictHostKeyChecking no

"@ | Out-File -FilePath $SSH_CONFIG_PATH -Append -Encoding utf8
        $VM_COUNT++
    }
}

Write-Host "SSH config updated with $($VM_COUNT-1) VMs for $TEAM_NAME."

# Step 6: Create helper scripts for common tasks
Write-Host "Step 6: Creating helper scripts for common tasks..."

# Create script for connecting to bastion host
@"
# PowerShell script to connect to the $TEAM_NAME bastion host
ssh ${TEAM_NAME}-bastion
"@ | Out-File -FilePath "connect_bastion.ps1" -Encoding utf8

# Create script for connecting to VMs
@"
# PowerShell script to connect to a $TEAM_NAME VM

# Check if VM number is provided
param(
    [Parameter(Mandatory=`$true)]
    [int]`$vmNumber
)

if (`$vmNumber -lt 1 -or `$vmNumber -gt $($VM_COUNT-1)) {
    Write-Host "Error: VM number must be between 1 and $($VM_COUNT-1)" -ForegroundColor Red
    exit 1
}

Write-Host "Connecting to ${TEAM_NAME}-vm`$vmNumber..."
ssh ${TEAM_NAME}-vm`$vmNumber
"@ | Out-File -FilePath "connect_vm.ps1" -Encoding utf8

# Create script for connecting to multiple VMs in separate terminals
@"
# PowerShell script to open connections to all $TEAM_NAME VMs in separate terminals

Write-Host "Opening connections to all VMs in separate PowerShell windows..."

# Connect to bastion host
Start-Process powershell -ArgumentList "-NoExit -File `".\connect_bastion.ps1`""

# Wait a bit for the bastion connection to establish
Start-Sleep -Seconds 2

# Connect to each VM
for (`$i=1; `$i -le $($VM_COUNT-1); `$i++) {
    Start-Process powershell -ArgumentList "-NoExit -File `".\connect_vm.ps1`" -vmNumber `$i"
    Start-Sleep -Seconds 1
}

Write-Host "Connection windows opened for bastion host and $($VM_COUNT-1) VMs."
"@ | Out-File -FilePath "connect_all.ps1" -Encoding utf8

# Create batch file wrappers for PowerShell scripts
@"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0connect_bastion.ps1"
"@ | Out-File -FilePath "connect_bastion.bat" -Encoding ascii

@"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0connect_vm.ps1" -vmNumber %1
"@ | Out-File -FilePath "connect_vm.bat" -Encoding ascii

@"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0connect_all.ps1"
"@ | Out-File -FilePath "connect_all.bat" -Encoding ascii

# Step 7: Test SSH connection to bastion host (if key was downloaded)
if ($keyDownloaded) {
    Write-Host "Step 7: Testing SSH connection to bastion host ($PUBLIC_IP)..."
    Write-Host "Attempting to connect (timeout 5 seconds, non-interactive)..."
    
    try {
        $result = ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i $KEY_PATH ubuntu@$PUBLIC_IP exit 2>$null
        Write-Host "Success: SSH connection to bastion host established!" -ForegroundColor Green
        $CONNECTION_SUCCESS = $true
    } catch {
        Write-Host "Warning: Could not establish SSH connection to bastion host." -ForegroundColor Yellow
        Write-Host "This could be due to:" -ForegroundColor Yellow
        Write-Host "1. The bastion host is not running or is unreachable." -ForegroundColor Yellow
        Write-Host "2. The SSH service on the bastion host is not running." -ForegroundColor Yellow
        Write-Host "3. A firewall is blocking the SSH connection." -ForegroundColor Yellow
        Write-Host "4. The SSH key is incorrect for this host." -ForegroundColor Yellow
        $CONNECTION_SUCCESS = $false
    }
} else {
    Write-Host "Step 7: Skipping SSH connection test as private key was not downloaded." -ForegroundColor Yellow
    $CONNECTION_SUCCESS = $false
}

# Step 8: Provide connection instructions
Write-Host ""
Write-Host "===== CONNECTION INSTRUCTIONS FOR $TEAM_NAME =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "The following helper scripts have been created in your team folder:" -ForegroundColor White
Write-Host ""
Write-Host "1. connect_bastion.bat or connect_bastion.ps1" -ForegroundColor White
Write-Host "   - Connects to the bastion host" -ForegroundColor White
Write-Host "   - Usage: .\connect_bastion.bat or .\connect_bastion.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. connect_vm.bat <vm_number> or connect_vm.ps1 -vmNumber <vm_number>" -ForegroundColor White
Write-Host "   - Connects to a specific VM through the bastion host" -ForegroundColor White
Write-Host "   - Usage: .\connect_vm.bat 1 or .\connect_vm.ps1 -vmNumber 1" -ForegroundColor White
Write-Host ""
Write-Host "3. connect_all.bat or connect_all.ps1" -ForegroundColor White
Write-Host "   - Opens connections to all VMs in separate terminals" -ForegroundColor White
Write-Host "   - Usage: .\connect_all.bat or .\connect_all.ps1" -ForegroundColor White
Write-Host ""
Write-Host "You can also use the SSH aliases set up in your SSH config:" -ForegroundColor White
Write-Host "- ssh ${TEAM_NAME}-bastion (connects to bastion host)" -ForegroundColor White
Write-Host "- ssh ${TEAM_NAME}-vm1 (connects to VM 1 through bastion host)" -ForegroundColor White
Write-Host "- ssh ${TEAM_NAME}-vm2 (connects to VM 2 through bastion host)" -ForegroundColor White
Write-Host "- etc." -ForegroundColor White
Write-Host ""

if ($CONNECTION_SUCCESS) {
    Write-Host "Setup complete! SSH connection to the bastion host was successful." -ForegroundColor Green
    Write-Host "You should now be able to connect to the private VMs through the bastion host." -ForegroundColor Green
} else {
    Write-Host "Setup partially complete. SSH connection to the bastion host could not be verified." -ForegroundColor Yellow
    Write-Host "Please check the error messages above and try to resolve any issues before connecting." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Note: If you encounter 'running scripts is disabled' errors, you may need to change the PowerShell execution policy." -ForegroundColor Yellow
Write-Host "To do this, run PowerShell as Administrator and execute: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned" -ForegroundColor Yellow
