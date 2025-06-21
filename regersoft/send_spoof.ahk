; Путь к файлу spoof.sh
filePath := "C:\Users\Vitalya\Desktop\regerrrrr\spoof.sh"

; Ждем, пока пользователь вручную откроет терминал в Android и введет:
; cat > /system/bin/spoof.sh
; Затем нажимает Enter и жмет F7 для старта скрипта

F7::
    FileRead, scriptContent, %filePath%
    ; AutoHotkey переводит \n в {Enter}, поэтому заменим \r\n и \n на {Enter}
    scriptContent := StrReplace(scriptContent, "`r`n", "`n")
    scriptContent := StrReplace(scriptContent, "`n", "{Enter}")
    SendRaw %scriptContent%
    ; В конце имитируем Ctrl+D (обычно в эмуляторе терминала это Ctrl+D, если нет — проверь!)
    SendInput, ^d
    return