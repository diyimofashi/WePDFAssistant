; ═══════════════════════════════════════════════════════════════
; PyPDF Inno Setup 安装脚本
; 用于创建 Windows 安装程序
; ═══════════════════════════════════════════════════════════════

[Setup]
; ==================== 应用信息 ====================
AppName=PDFAssistant
AppVersion=1.0.0
AppId=PDFAssistant
AppPublisher=YourName
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={commonpf}\PDFAssistant
DefaultGroupName=PDFAssistant
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=PDFAssistant-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; ==================== 安装选项 ====================
; 创建桌面快捷方式
ChangesAssociations=yes
; 允许安装后运行程序
; UninstallDisplayIcon={app}\start.exe

[Files]
; ==================== Application files ====================
Source: "dist\start.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; ==================== 快捷方式 ====================
Name: "{group}\PDFAssistant"; Filename: "{app}\start.exe"
Name: "{group}\卸载 PDFAssistant"; Filename: "{uninstallexe}"
Name: "{commondesktop}\PDFAssistant"; Filename: "{app}\start.exe"; Tasks: desktopicon

[Tasks]
; ==================== 安装任务 ====================
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"
Name: "fileassoc"; Description: "将 PDFAssistant 设为默认 PDF 阅读器"; GroupDescription: "文件关联:"; Flags: unchecked

[Registry]
; ==================== 文件关联 ====================
; 仅在选择了 fileassoc 任务时执行
Root: HKCR; Subkey: ".pdf"; ValueType: string; ValueName: ""; ValueData: "PDFAssistant.PDF"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "PDFAssistant.PDF"; ValueType: string; ValueName: ""; ValueData: "PDF 文档"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "PDFAssistant.PDF\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\start.exe,0"; Tasks: fileassoc
Root: HKCR; Subkey: "PDFAssistant.PDF\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\start.exe"" ""%1"""; Tasks: fileassoc
Root: HKCR; Subkey: "PDFAssistant.PDF\shell\print\command"; ValueType: string; ValueName: ""; ValueData: """{app}\start.exe"" -print ""%1"""; Tasks: fileassoc

; 使用 OpenWith 协议让用户设置默认程序
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: none; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".pdf\OpenWithProgids"; ValueType: string; ValueName: "PDFAssistant.PDF"; Tasks: fileassoc

[Run]
; ==================== 运行程序 ====================
Filename: "{app}\start.exe"; Description: "启动 PDFAssistant"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; ==================== 卸载清理 ====================
; 删除用户数据目录
Type: filesandordirs; Name: "{userappdata}\PDFAssistant"
; 删除缓存目录
Type: filesandordirs; Name: "{localappdata}\PDFAssistant"

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
    if MsgBox('检测到已安装旧版本的 PDFAssistant。' + #13#10 + #13#10 +
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
begin
  if CurStep = ssPostInstall then
  begin
    { 如果选择了 fileassoc 任务，调用默认应用设置 }
    if IsTaskSelected('fileassoc') then
    begin
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

// 卸载完成后
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
