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

; Настройка установки без обязательных прав администратора
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Types]
Name: "full"; Description: "Полная установка"
Name: "custom"; Description: "Выборочная установка"; Flags: iscustom

[Components]
Name: "main"; Description: "Интерпретатор RuPy (основные файлы)"; Types: full custom; Flags: fixed
Name: "path"; Description: "Добавить RuPy в локальную переменную PATH пользователя"; Types: full custom
Name: "context"; Description: "Добавить пункты в контекстное меню файлов .rupy"; Types: full custom

[Files]
Source: "dist\rupython.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main

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

// Глобальная переменная для чекбокса GitHub
var
  GitHubCheckBox: TNewCheckBox;

// Импорт функции WinAPI для обновления окружения
function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: Longint; lParam: String; fuFlags: UINT; uTimeout: UINT; out lpdwResult: DWORD): LongInt;
  external 'SendMessageTimeout{#AW}@user32.dll stdcall';

// Импорт функции WinAPI для безопасного открытия ссылок в обход багов shellexec
function ShellExecute(hWnd: HWND; lpOperation, lpFile, lpParameters, lpDirectory: String; nShowCmd: Integer): LongWord;
  external 'ShellExecuteW@shell32.dll stdcall';

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
  // Используем $FFFF вместо HWND_BROADCAST, чтобы избежать дублирования идентификаторов
  SendMessageTimeout($FFFF, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, dwResult);
end;

// Создаем галочку на финальной странице завершения
procedure InitializeWizard;
begin
  GitHubCheckBox := TNewCheckBox.Create(WizardForm);
  GitHubCheckBox.Parent := WizardForm.FinishedPage;
  GitHubCheckBox.Left := WizardForm.FinishedLabel.Left;
  GitHubCheckBox.Top := WizardForm.FinishedLabel.Top + WizardForm.FinishedLabel.Height + ScaleY(12);
  GitHubCheckBox.Width := WizardForm.FinishedLabel.Width;
  GitHubCheckBox.Height := ScaleY(20);
  GitHubCheckBox.Caption := 'Посетить страницу проекта на GitHub';
  GitHubCheckBox.Checked := True; // Галочка стоит по умолчанию
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Безопасное обновление PATH через setx
    if IsComponentSelected('path') then
    begin
      Exec('cmd.exe', '/c setx PATH "%PATH%;' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewNoWait, ResultCode);
    end;
    UpdateEnvironment;
  end;
end;

// Проверяем состояние галочки при полном закрытии установщика
procedure DeinitializeSetup;
begin
  if (GitHubCheckBox <> nil) and GitHubCheckBox.Checked then
  begin
    // Открываем браузер через чистое WinAPI без вызова ошибки 2147746293
    ShellExecute(0, 'open', 'https://github.com', '', '', 5); // 5 = SW_SHOW
  end;
end;

procedure CurUninstallStepChanged(JustAfterAnsi: TUninstallStep);
begin
  if JustAfterAnsi = usPostUninstall then
    UpdateEnvironment;
end;
