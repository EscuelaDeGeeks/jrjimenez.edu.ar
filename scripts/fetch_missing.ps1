$base = "https://juanramonjimenez-pulgarin.com"
$root = "C:\Code\jrjimenez.edu.ar"
$urls = @(
  "/wp-content/themes/hello-elementor/assets/css/reset.css?ver=3.4.4",
  "/wp-includes/js/jquery/jquery-migrate.min.js?ver=3.4.1",
  "/wp-content/uploads/2025/09/DSCF5133-scaled.jpg",
  "/wp-content/uploads/2025/09/BNZ_0650-1024x683.jpg",
  "/wp-content/uploads/2025/07/Historia5-1024x890.jpg",
  "/wp-content/uploads/2025/07/Historia5-1024x890.jpg",
  "/wp-content/plugins/elementor/assets/css/widget-social-icons.min.css?ver=3.30.0",
  "/wp-content/plugins/elementor/assets/lib/swiper/v8/css/swiper.min.css?ver=8.4.5",
  "/wp-content/plugins/ultimate-post-kit/assets/css/upk-site.css?ver=3.15.3",
  "/wp-content/uploads/elementor/google-fonts/css/montserrat.css?ver=1751768676"
)

function Get-LocalPath($path) {
  $q = ""
  if ($path -match "\?") {
    $parts = $path -split "\?", 2
    $path = $parts[0]
    $q = "@" + ($parts[1] -replace "/", "_")
  }
  if ($path -notmatch "\.[a-z0-9]+$" -and $path -notmatch "/$") { $path += ".html" }
  if ($path -match "/$") { $path += "index.html" }
  $rel = $path.TrimStart("/")
  if ($q) {
    $dir = Split-Path $rel -Parent
    $name = Split-Path $rel -Leaf
    if ($dir) { $rel = "$dir/${name}${q}" } else { $rel = "${name}${q}" }
  }
  return Join-Path $root $rel
}

foreach ($u in $urls) {
  $dest = Get-LocalPath $u
  $dir = Split-Path $dest -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  if (Test-Path $dest) { Write-Host "skip $u"; continue }
  Write-Host "get $u"
  curl -fsSL "$base$u" -o $dest
}

Get-ChildItem -Path $root -Recurse -Include *.html -File |
  Where-Object { $_.FullName -notmatch '\\\.git\\|\\scripts\\' } |
  ForEach-Object {
    $c = Get-Content $_.FullName -Raw -Encoding UTF8
    $n = $c -replace 'wp-includes_([^"''\s]+)', { param($m)
      $p = $m.Groups[1].Value -replace '_','/'
      "wp-includes/$p"
    }
    if ($n -ne $c) { Set-Content $_.FullName $n -Encoding UTF8 -NoNewline }
  }

Write-Host "done"