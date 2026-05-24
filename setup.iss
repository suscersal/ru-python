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

; Установка строго БЕЗ обязательных прав администратора (в реестр пользователя HKCU)
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

[Files]
; Укажите путь к скомпилированным файлам вашего проекта
Source: ".\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Components: startmenu
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"; Components: startmenu

[Registry]
; Запись в PATH пользователя с флагом сохранения оригинального типа строки
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{code:GetCleanPath}"; Check: NeedsAddPath; Components: path; Flags: preservestringtype

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


// ==========================================
// СЕКЦИЯ КОДА С ПРАВИЛЬНЫМ ПОРЯДКОМ ФУНКЦИЙ
// ==========================================
[Code]
#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif

const
  WM_SETTINGCHANGE = $001A;
  SMTO_ABORTIFHUNG = 2;

// Импорт функции WinAPI для обновления окружения проводника Windows без перезагрузки системы
function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: Longint; lParam: String; fuFlags: UINT; uTimeout: UINT; out lpdwResult: DWORD): LongInt;
  external 'SendMessageTimeout{#AW}@user32.dll stdcall';

// 1. Проверка необходимости добавления пути в реестр
function NeedsAddPath: Boolean;
var
  OrigPath: String;
  ParamPath: String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    Exit;
  end;
  OrigPath := Trim(UpperCase(OrigPath));
  ParamPath := Trim(UpperCase(ExpandConstant('{app}')));
  if Pos(';' + ParamPath + ';', ';' + OrigPath + ';') = 0 then
    Result := True
  else
    Result := False;
end;

// 2. Генерация чистой строки пути для секции [Registry]
function GetCleanPath(Param: String): String;
var
  CurrentPath: String;
  NewPath: String;
begin
  if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', CurrentPath) then
  begin
    CurrentPath := Trim(CurrentPath);
    NewPath := CurrentPath;
    
    // Проверяем, нужна ли точка с запятой в конце текущего PATH, чтобы пути не склеились
    if (NewPath <> '') and (NewPath[Length(NewPath)] <> ';') then
      NewPath := NewPath + ';';
      
    Result := NewPath + ExpandConstant('{app}');
  end
  else
  begin
    Result := ExpandConstant('{app}');
  end;
end;

// 3. Отправка широковещательного уведомления системе об изменении переменных
procedure UpdateEnvironment;
var
  dwResult: DWORD;
begin
  // Оповещаем систему и Проводник Windows о смене переменных окружения
  SendMessageTimeout($FFFF, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, dwResult);
end;

// Вызывается автоматически сразу после завершения процесса копирования файлов
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    UpdateEnvironment;
  end;
end;

// Вызывается автоматически сразу после удаления программы из системы
procedure CurUninstallStepChanged(JustAfterAnsi: TUninstallStep);
begin
  if JustAfterAnsi = usPostUninstall then
  begin
    UpdateEnvironment;
  end;
end;
