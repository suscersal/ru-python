#define MyAppName "RuPython"
#define MyAppVersion "1.0"
#define MyAppPublisher "SUSCERSAL"
#define MyAppExeName "rupython.exe"
#define MyAppId "{{EFD84A9D-E499-4EFB-B173-7ED63F9CC602}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
WizardStyle=modern
Compression=lzma
SolidCompression=yes
OutputDir=.\Setup_Build
OutputBaseFilename=rupyInstaller
ChangesAssociations=yes
SetupMutex={#MyAppId}_Mutex

; Установка строго БЕЗ обязательных прав администратора
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=dialog

; Отключаем лишнюю отдельную страницу выбора папки в Пуск
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Types]
Name: "full"; Description: "Полная установка"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Components]
Name: "main"; Description: "Интерпретатор RuPy (основные файлы)"; Types: full custom; Flags: fixed
Name: "startmenu"; Description: "Создать папку со ссылками в меню Пуск"; Types: full custom
Name: "path"; Description: "Добавить RuPy в локальную переменную PATH пользователя"; Types: full custom
Name: "context"; Description: "Добавить пункты в контекстное меню файлов .rupy"; Types: full custom

; --- Секция создания ярлыков в меню Пуск ---
; Ярлыки создаются только если выбрана галочка компонента "startmenu"
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Components: startmenu
Name: "{group}\Посетить GitHub проекта"; Filename: "https://github.com"; Components: startmenu
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"; Components: startmenu

[Registry]
; Запись в PATH
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath; Components: path

; --- Ассоциация файлов и Контекстное меню ---
Root: HKA; Subkey: "Software\Classes\.rupy"; ValueType: string; ValueName: ""; ValueData: "RuPy.File"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RuPy.File"; ValueType: string; ValueName: ""; ValueData: "Скрипт RuPython"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RuPy.File\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletevalue

; Команда по умолчанию (Двойной клик) — Запустить через RuPy
Root: HKA; Subkey: "Software\Classes\RuPy.File\shell\open"; ValueType: string; ValueName: ""; ValueData: "Запустить"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RuPy.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue

; --- Контекстное меню (Правая кнопка) — Открыть в VS Code ---
Root: HKA; Subkey: "Software\Classes\RuPy.File\shell\EditInVSCode"; ValueType: string; ValueName: ""; ValueData: "Открыть в VS Code"; Components: context; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RuPy.File\shell\EditInVSCode"; ValueType: string; ValueName: "Icon"; ValueData: """{localappdata}\Programs\Microsoft VS Code\Code.exe"""; Components: context; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\RuPy.File\shell\EditInVSCode\command"; ValueType: string; ValueName: ""; ValueData: """{localappdata}\Programs\Microsoft VS Code\Code.exe"" ""%1"""; Components: context; Flags: uninsdeletevalue

[Code]
#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif

const
  WM_SETTINGCHANGE = $001A;
  SMTO_ABORTIFHUNG = 2;

var
  GitHubCheckBox: TNewCheckBox;
  OpenGitHubOnClose: Boolean;

// Импорт функции WinAPI для обновления окружения
function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: Longint; lParam: String; fuFlags: UINT; uTimeout: UINT; out lpdwResult: DWORD): LongInt;
  external 'SendMessageTimeout{#AW}@user32.dll stdcall';

function NeedsAddPath: Boolean;
var
  OrigPath: String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + UpperCase(ExpandConstant('{app}')) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;

procedure UpdateEnvironment;
var
  dwResult: DWORD;
begin
  SendMessageTimeout($FFFF, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, dwResult);
end;


procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsComponentSelected('path') then
    begin
      Exec('cmd.exe', '/c setx PATH "%PATH%;' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewNoWait, ResultCode);
    end;
    UpdateEnvironment;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpFinished then
  begin
    if (GitHubCheckBox <> nil) and GitHubCheckBox.Checked then
    begin
      OpenGitHubOnClose := True;
    end;
  end;
end;

// Стопроцентный метод запуска ссылки через создание временного .url ярлыка Windows
procedure DeinitializeWizard;
var
  UrlLines: TArrayOfString;
  UrlPath: String;
  ResultCode: Integer;
begin
  if OpenGitHubOnClose then
  begin
    UrlPath := ExpandConstant('{tmp}\github.url');
    
    SetArrayLength(UrlLines, 3);
    UrlLines[0] := '[InternetShortcut]';
    UrlLines[1] := 'URL=https://github.com';
    UrlLines[2] := '';
    
    if SaveStringsToFile(UrlPath, UrlLines, False) then
    begin
      ShellExecAsOriginalUser('open', UrlPath, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
    end;
  end;
end;

procedure CurUninstallStepChanged(JustAfterAnsi: TUninstallStep);
begin
  if JustAfterAnsi = usPostUninstall then
    UpdateEnvironment;
end;
