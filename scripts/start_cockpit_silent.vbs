Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Mendapatkan direktori project memoriagraph
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
repoDir = fso.GetParentFolderName(scriptDir)

' Cari python virtualenv
dotVenvPython = repoDir & "\.venv\Scripts\pythonw.exe"
if Not fso.FileExists(dotVenvPython) Then
    dotVenvPython = repoDir & "\.venv\Scripts\python.exe"
End If

venvPython = repoDir & "\venv\Scripts\pythonw.exe"
if Not fso.FileExists(venvPython) Then
    venvPython = repoDir & "\venv\Scripts\python.exe"
End If

pythonExe = "python.exe"
If fso.FileExists(dotVenvPython) Then
    pythonExe = dotVenvPython
ElseIf fso.FileExists(venvPython) Then
    pythonExe = venvPython
End If

trayScript = repoDir & "\scripts\cockpit_tray.py"
cmd = """" & pythonExe & """ """ & trayScript & """"

' Jalankan di background tanpa memunculkan jendela console hitam (0 = Hide window)
WshShell.Run cmd, 0, False
