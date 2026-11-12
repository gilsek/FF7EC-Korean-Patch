@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo 관리자 권한이 필요합니다. 이 파일을 마우스 오른쪽 버튼으로 눌러 "관리자 권한으로 실행"하세요.
  pause
  exit /b 1
)
if not exist "ko_patch\files.txt" (
  echo ko_patch\files.txt가 없습니다. 이미 제거되었거나 게임 폴더가 아닙니다.
  pause
  exit /b 1
)
tasklist /fi "imagename eq FF7EC.exe" | find /i "FF7EC.exe" >nul && (
  echo 게임이 실행 중입니다. 게임을 끈 뒤 다시 실행하세요.
  pause
  exit /b 1
)

echo FF7EC 한글패치를 제거합니다. 계속하려면 아무 키나 누르세요. (취소: 창 닫기)
pause >nul

echo [1/3] 폰트 원본 복구
if exist "ko_patch\FontPatch.exe" (
  "ko_patch\FontPatch.exe" --game "%~dp0." --restore
  if errorlevel 1 (
    echo 폰트 복구에 실패했습니다. ko_patch\fontpatch.log를 확인하세요. 제거를 중단합니다.
    pause
    exit /b 1
  )
)

echo [2/3] 패치 파일 삭제
copy /y "ko_patch\files.txt" "%TEMP%\ff7ec_ko_files.txt" >nul
for /f "usebackq delims=" %%f in ("%TEMP%\ff7ec_ko_files.txt") do (
  if /i not "%%f"=="uninstall_ko.bat" if exist "%%f" del /f /q "%%f"
)
del /f /q "%TEMP%\ff7ec_ko_files.txt" >nul 2>&1

echo [3/3] BepInEx가 만든 파일 정리
for %%d in ("BepInEx\interop" "BepInEx\unity-libs" "BepInEx\cache" "BepInEx\Translation" "BepInEx\config" "BepInEx\patchers" "BepInEx\plugins" "BepInEx\core" "ko_patch" "dotnet" "LICENSES") do (
  if exist %%d rmdir /s /q %%d
)
for %%f in ("BepInEx\LogOutput.log" "BepInEx\ErrorLog.log" "ff7ec_ko_launcher.log" "ff7ec_ko_server.log") do (
  if exist %%f del /f /q %%f
)
rmdir "BepInEx" >nul 2>&1

echo.
echo 제거가 끝났습니다. 이 파일(uninstall_ko.bat)은 직접 지워 주세요.
echo 게임은 이제 FF7ECServer.exe로 실행하면 됩니다.
pause
