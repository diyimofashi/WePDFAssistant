; ═══════════════════════════════════════════════════════════════
; PyPDF Inno Setup 安装脚本
; 用于创建 Windows 安装程序
; ═══════════════════════════════════════════════════════════════
#define MyAppName "PDFAssistant"
#define MyAppVer  "1.0.0"
#define MyAppExe  "PDFAssistant.exe"

[Setup]
; ==================== 应用信息 ====================
AppName={#MyAppName}
AppVersion={#MyAppVer}
AppId={#MyAppName}
AppPublisher=Cash
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVer}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=app\assets\app_icon.ico
UninstallDisplayIcon={app}\start.exe
; ==================== 语言和界面 ====================
ShowLanguageDialog=no
ShowComponentSizes=no
; ==================== 许可协议 ====================
LicenseFile=app\assets\LICENSE.txt

; ==================== 安装选项 ====================
; 创建桌面快捷方式
ChangesAssociations=yes
; 允许安装后运行程序
; UninstallDisplayIcon={app}\start.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
; ==================== Application files ====================
Source: "dist\start.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; ==================== 快捷方式 ====================
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: quicklaunch

[Tasks]
; ==================== 安装任务 ====================
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "创建桌面快捷方式:"
Name: "quicklaunch"; Description: "添加到快速启动栏"; GroupDescription: "添加到快速启动栏:"; Flags: unchecked
Name: "fileassoc"; Description: "将 PDFAssistant 设为默认 PDF 阅读器"; GroupDescription: "文件关联:"; Flags: unchecked

[Registry]
; ==================== 文件关联 ====================
; 仅在选择了 fileassoc 任务时执行
Root: HKCR; Subkey: ".pdf"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName}.PDF"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF"; ValueType: string; ValueName: ""; ValueData: "PDF 文档"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExe},0"; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\shell"; ValueType: string; ValueName: ""; ValueData: "使用 {#MyAppName} 打开"; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\shell\open"; ValueType: string; ValueName: ""; ValueData: "打开"; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\shell\print"; ValueType: string; ValueName: ""; ValueData: "打印"; Tasks: fileassoc
Root: HKCR; Subkey: "{#MyAppName}.PDF\shell\print\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" -print ""%1"""; Tasks: fileassoc

; 使用 OpenWith 协议让用户设置默认程序
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: none; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppName}.PDF"; Tasks: fileassoc

; 添加应用程序注册信息
Root: HKCR; Subkey: "Applications\{#MyAppExe}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName}"; Tasks: fileassoc
Root: HKCR; Subkey: "Applications\{#MyAppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; Tasks: fileassoc
Root: HKCR; Subkey: "Applications\{#MyAppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""; Tasks: fileassoc

; 注册应用程序到系统（用于默认应用显示）
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExe}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExe}"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExe}"; ValueType: string; ValueName: "PrettyName"; ValueData: "{#MyAppName}"; Tasks: fileassoc
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExe}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Tasks: fileassoc
Root: HKLM; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "Software\{#MyAppName}\Capabilities"; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "{#MyAppName} - PDF 阅读器"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#MyAppName}.PDF"; Tasks: fileassoc

[Run]
; ==================== 运行程序 ====================
Filename: "{app}\{#MyAppExe}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; ==================== 卸载清理 ====================
; 删除用户数据目录
;Type: filesandordirs; Name: "{userappdata}\{#MyAppName}"
; 删除缓存目录
;Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Code]

{ ==================== Pascal 脚本 ==================== }

{ 初始化安装程序 }
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstallString: String;
begin
  Result := True;

  { 检查是否已安装旧版本 }
  if RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1') then
  begin
    if MsgBox('检测到已安装旧版本的 {#MyAppName}。' + #13#10 + #13#10 +
              '是否要卸载旧版本并继续安装？',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      { 获取卸载程序路径 }
      if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1', 'UninstallString', UninstallString) then
      begin
        { 提取卸载程序路径（去掉引号和参数） }
        UninstallString := RemoveQuotes(UninstallString);
        { 运行卸载程序 }
        if not Exec(UninstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES',
                    '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) then
        begin
          { 卸载失败，可能是卸载程序不存在或被删除 }
          if MsgBox('卸载程序未找到或已删除。' + #13#10 + #13#10 +
                 '是否继续安装覆盖旧版本？' + #13#10 +
                 '（建议先手动卸载旧版本）',
                 mbConfirmation, MB_YESNO) = IDYES then
            Result := True
          else
            Result := False;
        end
        else if ResultCode <> 0 then
        begin
          if MsgBox('卸载失败，错误代码: ' + IntToStr(ResultCode) + #13#10 + #13#10 +
                 '是否继续安装覆盖旧版本？',
                 mbConfirmation, MB_YESNO) = IDYES then
            Result := True
          else
            Result := False;
        end;
      end
      else
      begin
        { 无法获取卸载程序路径 }
        if MsgBox('无法获取卸载程序信息。' + #13#10 + #13#10 +
               '是否继续安装覆盖旧版本？',
               mbConfirmation, MB_YESNO) = IDYES then
          Result := True
        else
          Result := False;
      end;
    end
    else
    begin
      Result := False;
    end;
  end;
end;

{ 安装后设置默认程序 }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  RegKey: String;
begin
  if CurStep = ssPostInstall then
  begin
    { 如果选择了 fileassoc 任务，设置应用程序描述 }
    if IsTaskSelected('fileassoc') then
    begin
      { 在 App Paths 中注册应用程序，这有助于系统识别应用名称 }
      RegKey := 'Software\Microsoft\Windows\CurrentVersion\App Paths\PDFAssistant.exe';
      RegWriteStringValue(HKLM, RegKey, '', ExpandConstant('{app}\PDFAssistant.exe'));
      RegWriteStringValue(HKLM, RegKey, 'Path', ExpandConstant('{app}'));
      RegWriteStringValue(HKLM, RegKey, 'PrettyName', 'PDFAssistant');

      { 注册应用程序到系统应用列表 }
      RegKey := 'Software\RegisteredApplications';
      RegWriteStringValue(HKLM, RegKey, 'PDFAssistant', 'Software\PDFAssistant\Capabilities');

      { 添加应用程序能力 }
      RegKey := 'Software\PDFAssistant\Capabilities';
      RegWriteStringValue(HKLM, RegKey, 'ApplicationDescription', 'PDFAssistant - PDF 阅读器');

      RegKey := 'Software\PDFAssistant\Capabilities\FileAssociations';
      RegWriteStringValue(HKLM, RegKey, '.pdf', 'PDFAssistant.PDF');

      { 打开默认应用设置页面 }
      ShellExec('open', 'control', '/name Microsoft.DefaultPrograms /page pageDefaultProgram', '', SW_SHOW, ewNoWait, ResultCode);
      MsgBox('PDFAssistant 已注册为 PDF 打开程序。' + #13#10 + #13#10 +
             '请在打开的默认应用设置页面中，选择 PDFAssistant 作为 PDF 文件的默认打开程序。',
             mbInformation, MB_OK);
    end;
  end;
end;

{ 卸载前询问是否删除用户数据 }
function UninstallNeedRestart(): Boolean;
begin
  Result := False;
end;

{ 卸载完成后 }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('是否删除用户数据和配置文件？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UserDir := ExpandConstant('{userappdata}\PDFAssistant');
      if DirExists(UserDir) then
        DelTree(UserDir, True, True, True);
    end;

    if MsgBox('是否删除缓存和日志文件？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UserDir := ExpandConstant('{localappdata}\PDFAssistant');
      if DirExists(UserDir) then
        DelTree(UserDir, True, True, True);
    end;

    { 清理应用程序注册信息 }
    RegDeleteKeyIncludingSubkeys(HKLM, 'Software\PDFAssistant\Capabilities');
    RegDeleteKeyIncludingSubkeys(HKLM, 'Software\PDFAssistant');
    RegDeleteKeyIncludingSubkeys(HKLM, 'Software\Microsoft\Windows\CurrentVersion\App Paths\PDFAssistant.exe');
  end;
end;

// 跳过页面
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  // 跳过选择开始菜单文件夹页面（使用默认值）
  if PageID = wpSelectProgramGroup then
    Result := True
  else
    Result := False;
end;
