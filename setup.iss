#define MyAppName "RuPython"
#define MyAppVersion "1.0"
#define MyAppPublisher "SUSCERSAL"
#define MyAppExeName "rupython.exe"
; ID для идентификации программы (можешь сгенерировать свой Ctrl+Shift+G)
#define MyAppId "EFD84A9D-E499-4EFB-B173-7ED63F9CC602"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Современный стиль интерфейса
WizardStyle=modern
Compression=lzma
SolidCompression=yes
OutputDir=./Setup_Build
OutputBaseFilename=rupyInstaller
SetupIconFile=setup.ico

; SetupIconFile=icon.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Types]
Name: "full"; Description: "Полная установка"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Components]
Name: "main"; Description: "Интерпретатор RuPy (основные файлы)"; Types: full custom; Flags: fixed
Name: "vscode"; Description: "Расширение для VS Code"; Types: full custom
Name: "path"; Description: "Добавить RuPy в системную переменную PATH"; Types: full custom

[Files]
; 1. Сам транслятор (убедись, что он лежит в этой папке)
Source: "dist/rupy.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main
; 2. Расширение VS Code (копируем всю папку со всеми вложенными файлами)
Source: "rus-python\*"; DestDir: "{userappdata}\.vscode\extensions\rus-python"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: vscode

[Registry]
; Запись в PATH для текущего пользователя
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}'); Components: path

[Code]
// Объявляем системную функцию для обновления окружения
function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: LongInt; lParam: String; fuFlags: UINT; uTimeout: UINT; out lpdwResult: LongInt): LongInt;
  external 'SendMessageTimeoutW@user32.dll stdcall';

// Проверка, чтобы не добавлять один и тот же путь дважды
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + UpperCase(Param) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;

// Обновление окружения системы
procedure CurStepChanged(CurStep: TSetupStep);
var
  dwResult: LongInt;
begin
  if CurStep = ssPostInstall then
    // $001A - это WM_SETTINGCHANGE. Сообщаем системе, что PATH обновился.
    SendMessageTimeout(HWND_BROADCAST, $001A, 0, 'Environment', 2, 5000, dwResult);
end;



[Run]
; Предложение запустить после установки
; Filename: "{app}\{#MyAppExeName}"; Description: "Запустить консоль RuPy"; Flags: nowait postinstall skipifsilent
